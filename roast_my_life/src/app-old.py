import os
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
import requests

from pydantic import BaseModel, Field
from typing import List, Literal
from openai import OpenAI


# Pydantic models for structured phrase extraction
class ExtractedPhrase(BaseModel):
    """A single interesting phrase or fact from the video."""
    phrase: str = Field(description="The exact phrase, idiom, or claim from the video")
    timestamp: int = Field(description="Timestamp in seconds where this appears")
    context: str = Field(description="Brief context about what's happening")
    category: Literal["language_learning", "fact_check", "historical", "statistical", "cultural"] = Field(
        description="Category: language_learning for phrases/idioms, fact_check for verifiable claims"
    )
    reason: str = Field(description="Why this is interesting to learn or verify")
    language: str = Field(default="unknown", description="The language this phrase is in")

class VideoAnalysis(BaseModel):
    """Complete analysis of interesting phrases and facts from a video."""
    primary_language: str = Field(description="The main language spoken in the video")
    video_topic: str = Field(description="Brief description of what the video is about")
    items: List[ExtractedPhrase] = Field(
        description="List of 5-10 most interesting phrases and facts",
        max_length=10
    )

app = Flask(__name__)

load_dotenv()
api_key = os.environ.get('API_KEY')
base_url = os.environ.get('BASE_URL')

# Endpoint for the external chat/vision agent API. If needed this can be
# overridden via env; otherwise we default to using base_url + /qa/chat
REKA_VIDEO_QA_ENDPOINT = os.environ.get(
    'REKA_VIDEO_QA_ENDPOINT', 
    f"{base_url.rstrip('/')}/qa/chat"
)

# Simple in-memory cache for videos to avoid hitting the API on every request.
_VIDEO_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "ttl": 60.0,
    "results": []
}


def fetch_videos() -> List[Dict[str, Any]]:
    """
    Fetch the list of videos from Reka Vision API, with basic caching.

    The API is expected to respond with a JSON structure containing a
    "results" key that holds a list of video objects. Each video includes
    metadata with fields like "title" and "thumbnail".

    Returns:
        List[Dict[str, Any]]: List of video dictionaries from the API.
    """
    now = time.time()
    is_stale = (now - _VIDEO_CACHE["timestamp"]) > _VIDEO_CACHE["ttl"]

    if not base_url:
        # Without BASE_URL we can't call the API; return empty.
        return []

    url = f"{base_url.rstrip('/')}/videos/get"
    headers = {}
    if api_key:
        headers["X-Api-Key"] = api_key

    try:
        response = requests.post(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        _VIDEO_CACHE.update({
            "timestamp": now,
            "results": results
        })
        return results
    except Exception as e:
        # On failure, keep old cache if available; otherwise empty list.
        if _VIDEO_CACHE["results"]:
            return _VIDEO_CACHE["results"]
        return []


def call_reka_vision_qa(video_id: str, custom_prompt: str = None) -> Dict[str, Any]:
    """Call the Reka Video QA API for a given video.

    Parameters:
        video_id (str): The UUID of the video to query.
        custom_prompt (str): Optional custom user prompt. If None, uses default roast prompt.

    Returns:
        Dict[str, Any]: Parsed JSON response
    """
    headers = {}
    if api_key:
        headers['X-Api-Key'] = api_key

    # Use custom prompt or default to roast
    user_prompt = custom_prompt or "Write a funny and gently roast about the person, or the voice in this video. Reply in a markdown format."

    payload = {
        "video_id": video_id,
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }

    try:
        resp = requests.post(
            REKA_VIDEO_QA_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30
        )
        try:
            data = resp.json()
        except Exception:
            data = {"error": f"Non-JSON response (status {resp.status_code})"}

        if not resp.ok and 'error' not in data:
            data['error'] = f"HTTP {resp.status_code} calling chat endpoint"
        return data
    except requests.Timeout:
        return {"error": "Request to chat API timed out"}
    except Exception as e:
        return {"error": f"Chat API call failed: {e}"}

def simple_markdown_to_html(md: str) -> str:
    """
    Convert Markdown text to HTML using the Python-Markdown library.

    This function uses the 'markdown' package for robust Markdown parsing and HTML output.
    Any HTML in the source is safely handled by the library to mitigate injection risks.

    Parameters:
        md (str): Markdown input string.

    Returns:
        str: HTML output.
    """
    if not md:
        return ""
    import markdown
    # Use 'extra' and 'sane_lists' extensions for better Markdown support
    return markdown.markdown(md, extensions=['extra', 'sane_lists'])


@app.route('/')
def home() -> str:
    """
    Render the home page with welcome text.

    Returns:
        str: Rendered HTML template for the home page.
    """
    return render_template('index.html')


@app.route('/form')
def form_page() -> str:
    """
    Render the form page with dynamic video selection grid.

    Returns:
        str: Rendered HTML template for the form page.
    """
    videos = fetch_videos()

    # Transform videos to a simplified structure for the template.
    template_videos = []
    for v in videos:
        meta = v.get("metadata", {})
        template_videos.append({
            "id": v.get("video_id"),
            "name": meta.get("title") or meta.get("video_name") or "Untitled",
            # fallback
            "thumbnail": meta.get("thumbnail") or "/static/images/image1.jpg",
            "url": v.get("url") or meta.get("url") or "",
        })

    return render_template('form.html', videos=template_videos)


@app.route('/api/analyze_video', methods=['POST'])
def analyze_video() -> Dict[str, Any]:
    """
    Automatically analyze a video to extract interesting phrases and facts.
    """
    data = request.get_json() or {}
    video_id = data.get('video_id')
    
    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400
    
    try:
        # Build the analysis prompt with clear JSON instructions
        analysis_prompt = """Analyze this video and identify interesting content for language learning and fact verification.

Extract 5-10 items including:

**Language Learning Items:**
- Useful phrases, idioms, or expressions
- Slang or colloquialisms
- Important vocabulary
- Cultural references

**Fact Checking Items:**
- Historical facts or dates
- Statistics or claims
- Names of people, places, events
- Scientific statements

For each item, provide:
1. The exact phrase or claim
2. Timestamp in seconds where it appears
3. Brief context
4. Category (language_learning or fact_check)
5. Why it's interesting

IMPORTANT: Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{
  "primary_language": "detected language name",
  "video_topic": "brief description of video content",
  "items": [
    {
      "phrase": "exact phrase or claim from video",
      "timestamp": 120,
      "context": "what's happening in this moment",
      "category": "language_learning",
      "reason": "why this is interesting to learn",
      "language": "language name"
    }
  ]
}"""

        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "video_id": video_id,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing video content. Always respond with valid JSON only, no additional text or formatting."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ]
        }
        
        print(f"Analyzing video: {video_id}")
        
        resp = requests.post(
            REKA_VIDEO_QA_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        print(f"Response status: {resp.status_code}")
        
        try:
            response_data = resp.json()
        except Exception as e:
            print(f"JSON parse error: {e}")
            return jsonify({"error": f"Failed to parse API response: {str(e)}"}), 500
        
        if resp.ok:
            chat_response = response_data.get('chat_response')
            
            if not chat_response:
                print("No chat_response in data")
                # Return empty result instead of error
                return jsonify({
                    "success": True,
                    "primary_language": "Unknown",
                    "video_topic": "Analysis unavailable",
                    "items": []
                })
            
            print(f"Chat response preview: {str(chat_response)[:200]}")
            
            # Parse the JSON response
            try:
                import json
                import re
                
                # If it's already a dict, use it
                if isinstance(chat_response, dict):
                    parsed = chat_response
                else:
                    # Convert to string
                    chat_str = str(chat_response)
                    
                    # Remove markdown code blocks if present
                    chat_str = re.sub(r'```json\s*', '', chat_str)
                    chat_str = re.sub(r'```\s*', '', chat_str)
                    
                    # Try to find JSON object
                    json_match = re.search(r'\{[^{]*"items"[^}]*\[[^\]]*\][^}]*\}', chat_str, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        parsed = json.loads(json_str)
                    else:
                        # Try parsing whole response
                        parsed = json.loads(chat_str.strip())
                
                # Extract and validate items
                items = parsed.get('items', [])
                primary_language = parsed.get('primary_language', 'Unknown')
                video_topic = parsed.get('video_topic', 'Video content')
                
                print(f"Successfully extracted {len(items)} items")
                
                # Clean and validate items
                cleaned_items = []
                for item in items:
                    if isinstance(item, dict):
                        cleaned_items.append({
                            "phrase": str(item.get('phrase', '')),
                            "timestamp": int(item.get('timestamp', 0)),
                            "context": str(item.get('context', '')),
                            "category": str(item.get('category', 'language_learning')),
                            "reason": str(item.get('reason', '')),
                            "language": str(item.get('language', primary_language))
                        })
                
                return jsonify({
                    "success": True,
                    "primary_language": primary_language,
                    "video_topic": video_topic,
                    "items": cleaned_items
                })
                
            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                print(f"Parse error: {e}")
                print(f"Raw response: {chat_response}")
                
                # Return success with empty items
                return jsonify({
                    "success": True,
                    "primary_language": "Unknown",
                    "video_topic": "Could not analyze video",
                    "items": [],
                    "parse_error": str(e)
                })
            
        else:
            error_msg = response_data.get('error') or f"HTTP {resp.status_code}"
            print(f"API error: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"Analysis failed: {error_msg}"
            }), resp.status_code
            
    except requests.Timeout:
        print("Request timeout")
        return jsonify({
            "success": False,
            "error": "Analysis timed out"
        }), 504
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }), 500


@app.route('/api/explore_phrase', methods=['POST'])
def explore_phrase() -> Dict[str, Any]:
    """
    Deep dive into a phrase by:
    1. Getting detailed context from the video (Video QA)
    2. Researching additional information from the web (Reka Research)
    3. Combining both for comprehensive understanding
    """
    data = request.get_json() or {}
    video_id = data.get('video_id')
    phrase_data = data.get('phrase_data')
    
    if not video_id or not phrase_data:
        return jsonify({"error": "Missing video_id or phrase_data"}), 400
    
    phrase = phrase_data.get('phrase', '')
    timestamp = phrase_data.get('timestamp', 0)
    category = phrase_data.get('category', 'language_learning')
    context = phrase_data.get('context', '')
    
    try:
        # STEP 1: Get detailed context from video using Video QA
        print(f"Step 1: Analyzing phrase '{phrase}' in video at {timestamp}s")
        
        video_prompt = f"""Analyze this specific moment in the video at around {timestamp} seconds.

Focus on the phrase: "{phrase}"

Provide:
1. The exact context - what's happening when this is said
2. Who says it and why
3. The tone and emotion
4. Any visual context that's relevant
5. How this phrase fits into the conversation

Be detailed and specific."""

        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        video_payload = {
            "video_id": video_id,
            "messages": [
                {
                    "role": "user",
                    "content": video_prompt
                }
            ]
        }
        
        video_resp = requests.post(
            REKA_VIDEO_QA_ENDPOINT,
            headers=headers,
            json=video_payload,
            timeout=60
        )
        
        video_data = video_resp.json() if video_resp.ok else {}
        video_context = video_data.get('chat_response', 'Could not retrieve video context')
        
        # Handle structured response if present
        if isinstance(video_context, str) and video_context.strip().startswith('{'):
            try:
                import json
                parsed = json.loads(video_context)
                if 'sections' in parsed:
                    content_parts = []
                    for section in parsed.get('sections', []):
                        if isinstance(section, dict):
                            content = section.get('section_content')
                            if isinstance(content, str):
                                content_parts.append(content)
                    if content_parts:
                        video_context = '\n\n'.join(content_parts)
            except:
                pass
        
        print(f"Video context retrieved: {len(str(video_context))} chars")
        
        # STEP 2: Research additional information using Reka Research
        print(f"Step 2: Researching '{phrase}' on the web")
        
        # Initialize OpenAI client for Reka Research
        from openai import OpenAI
        client = OpenAI(
            base_url="https://api.reka.ai/v1",
            api_key=api_key
        )
        
        # Build research prompt based on category
        if category == 'language_learning':
            research_prompt = f"""Research this phrase for language learning: "{phrase}"

From the video, we learned: {context}

Please research and provide:
1. **Definition & Meaning**: What does this phrase mean?
2. **Usage Examples**: How is it commonly used? (Find real examples)
3. **Grammar Notes**: Any grammar patterns or rules
4. **Similar Expressions**: Related phrases or synonyms
5. **Cultural Context**: Cultural significance or origins
6. **Common Mistakes**: What learners should watch out for
7. **Practice Scenarios**: When and how to use this phrase

Use web sources to verify and expand on the information."""

        else:  # fact_check, historical, statistical
            research_prompt = f"""Verify and research this claim from a video: "{phrase}"

Video context: {context}

Please research and provide:
1. **Verification**: Is this claim accurate? What do authoritative sources say?
2. **Additional Facts**: Related information and context
3. **Sources**: What are the primary sources for this information?
4. **Nuances**: Are there any important details or qualifications?
5. **Related Information**: Connected facts or events
6. **Common Misconceptions**: What do people often get wrong about this?

Use web sources to fact-check and provide authoritative information."""

        # Call Reka Research
        research_completion = client.chat.completions.create(
            model="reka-flash-research",
            messages=[
                {
                    "role": "user",
                    "content": research_prompt
                }
            ],
            timeout=90
        )
        
        web_research = research_completion.choices[0].message.content
        
        print(f"Web research retrieved: {len(str(web_research))} chars")
        
        # STEP 3: Combine both contexts into a comprehensive response
        combined_response = f"""## 📹 From the Video

{video_context}

---

## 🌐 Additional Research

{web_research}"""

        # Convert to HTML
        html_response = simple_markdown_to_html(combined_response)
        
        return jsonify({
            "success": True,
            "response": html_response,
            "raw_response": combined_response,
            "video_context": str(video_context),
            "web_research": str(web_research)
        })
        
    except Exception as e:
        print(f"Error in explore_phrase: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Failed to explore phrase: {str(e)}"
        }), 500

@app.route('/api/upload_video', methods=['POST'])
def upload_video() -> Dict[str, Any]:
    """
    Upload a new video to the Reka Vision API.

    Expects JSON body: { "video_name": "string", "video_url": "string" }

    Returns:
        Dict[str, Any]: JSON response with fields:
            success (bool)
            video_id (str) when successful
            error (str) when not successful
    """
    data = request.get_json() or {}
    video_name = data.get('video_name', '').strip()
    video_url = data.get('video_url', '').strip()

    if not video_name or not video_url:
        return jsonify({"error": "Both video_name and video_url are required"}), 400

    if not api_key:
        return jsonify({"error": "API key not configured"}), 500

    # Call Reka API to upload video
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/videos/upload",
            headers={
                "X-Api-Key": api_key
            },
            data={
                'video_name': video_name,
                'index': 'true',
                'video_url': video_url
            },
            timeout=30
        )
        
        # Try to parse the response
        try:
            response_data = response.json()
        except Exception:
            response_data = {}

        if response.ok:
            # Invalidate cache to force refresh
            _VIDEO_CACHE["timestamp"] = 0.0
            
            video_id = response_data.get('video_id', 'unknown')
            return jsonify({
                "success": True, 
                "video_id": video_id,
                "message": "Video uploaded successfully"
            })
        else:
            error_msg = response_data.get('error') or response_data.get('message') or f"HTTP {response.status_code}"
            return jsonify({"success": False, "error": f"Upload failed: {error_msg}"}), response.status_code

    except requests.Timeout:
        return jsonify({"success": False, "error": "Request timed out"}), 504
    except Exception as e:
        return jsonify({"success": False, "error": f"Upload failed: {str(e)}"}), 500


# Add this constant at the top of your app.py after imports
LANGUAGE_TUTOR_SYSTEM_PROMPT = """You are an expert language tutor helping non-native speakers improve their language skills through video content.

Your role:
1. First, identify the language being spoken in the video
2. Analyze the dialogue, pronunciation, grammar, and vocabulary used
3. Provide helpful learning insights tailored to that specific language
4. Point out interesting phrases, idioms, or cultural context
5. Explain difficult words or expressions
6. Highlight good examples of natural language usage

When responding:
- Be encouraging and supportive
- Use specific timestamps to reference parts of the video
- Explain grammar points when relevant
- Suggest practice exercises based on the content
- Note any regional accents or dialects
- Point out common mistakes non-native speakers make with similar phrases

Keep your tone friendly, educational, and motivating. Focus on practical learning that helps the student improve their comprehension and speaking skills."""


@app.route('/api/chat', methods=['POST'])
def chat_with_video() -> Dict[str, Any]:
    """
    Chat with a video using the Reka Video QA API as a language tutor.
    """
    data = request.get_json() or {}
    video_id = data.get('video_id')
    user_message = data.get('message', '').strip()
    conversation_history = data.get('conversation_history', [])
    
    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    # Build messages array with system prompt
    messages = []
    
    # Add system prompt at the very beginning if this is the first message
    if len(conversation_history) == 0:
        messages.append({
            "role": "system",
            "content": LANGUAGE_TUTOR_SYSTEM_PROMPT
        })
    
    # Add previous conversation messages
    for msg in conversation_history:
        messages.append({
            "role": msg.get("role"),
            "content": msg.get("content")
        })
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "video_id": video_id,
        "messages": messages
    }
    
    try:
        resp = requests.post(
            REKA_VIDEO_QA_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        try:
            response_data = resp.json()
        except Exception:
            response_data = {"error": f"Non-JSON response (status {resp.status_code})"}
        
        if resp.ok:
            chat_response = response_data.get('chat_response')
            system_message = response_data.get('system_message')
            api_error = response_data.get('error')
            status = response_data.get('status')
            
            if api_error:
                return jsonify({"error": f"API error: {api_error}"}), 500
            
            if status and status != 'success':
                return jsonify({"error": f"API status: {status}"}), 500
            
            if chat_response:
                response_text = chat_response
                
                # Handle structured JSON response
                if isinstance(chat_response, str) and chat_response.strip().startswith('{'):
                    try:
                        import json
                        parsed = json.loads(chat_response)
                        
                        if isinstance(parsed, dict) and 'sections' in parsed:
                            sections = parsed.get('sections', [])
                            content_parts = []
                            
                            for section in sections:
                                if isinstance(section, dict) and 'section_content' in section:
                                    content = section['section_content']
                                    
                                    if isinstance(content, str):
                                        content_parts.append(content)
                                    
                                    elif isinstance(content, dict) and 'video_clips' in content:
                                        clips_markdown = []
                                        for clip in content['video_clips']:
                                            start = clip.get('video_clip_start_time', 0)
                                            end = clip.get('video_clip_end_time', 0)
                                            info = clip.get('video_clip_info', '')
                                            clips_markdown.append(
                                                f"**⏱️ [{start}s - {end}s]**: {info}"
                                            )
                                        if clips_markdown:
                                            content_parts.append('\n\n'.join(clips_markdown))
                            
                            if content_parts:
                                response_text = '\n\n'.join(content_parts)
                    
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                html_response = simple_markdown_to_html(response_text)
                
                return jsonify({
                    "success": True, 
                    "response": html_response,
                    "raw_response": response_text
                })
            
            elif system_message:
                html_response = simple_markdown_to_html(system_message)
                return jsonify({
                    "success": True,
                    "response": html_response,
                    "raw_response": system_message
                })
            
            else:
                error_msg = f"No response content. Status: {status}"
                return jsonify({"error": error_msg}), 500
                
        else:
            error_msg = response_data.get('error') or response_data.get('message') or f"HTTP {resp.status_code}"
            return jsonify({"error": f"Chat failed: {error_msg}"}), resp.status_code
            
    except requests.Timeout:
        return jsonify({"error": "Request timed out"}), 504
    except Exception as e:
        return jsonify({"error": f"Chat failed: {str(e)}"}), 500

@app.route('/chat/<video_id>')
def chat_page(video_id: str) -> str:
    """
    Render the chat interface for a specific video.
    
    Args:
        video_id: UUID of the video to chat about
        
    Returns:
        str: Rendered HTML template for the chat page
    """
    videos = fetch_videos()
    
    # Find the video
    video = None
    for v in videos:
        if v.get("video_id") == video_id:
            meta = v.get("metadata", {})
            video = {
                "id": v.get("video_id"),
                "name": meta.get("title") or meta.get("video_name") or "Untitled",
                "thumbnail": meta.get("thumbnail") or "/static/images/image1.jpg",
                "url": v.get("url") or meta.get("url") or "",
            }
            break
    
    if not video:
        return "Video not found", 404
    
    return render_template('chat.html', video=video)

@app.route('/api/process', methods=['POST'])
def process_video() -> Dict[str, Any]:
    """
    Process the selected video by calling the external Reka chat API.
    """
    data = request.get_json() or {}
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400

    api_data = call_reka_vision_qa(video_id)

    # Determine final message to surface.
    chat_response = api_data.get('chat_response')
    system_msg = api_data.get('system_message')
    api_error = api_data.get('error')

    if chat_response:
        roast_content = chat_response

        # Parse the JSON string to extract section content
        if isinstance(chat_response, str):
            try:
                import json
                parsed = json.loads(chat_response)
                if isinstance(parsed, dict) and 'sections' in parsed:
                    sections = parsed.get('sections', [])
                    content_parts = []
                    for section in sections:
                        if isinstance(section, dict) and 'section_content' in section:
                            content = section['section_content']
                            # Only add if it's a string (markdown sections)
                            if isinstance(content, str):
                                content_parts.append(content)
                            # For dict content (like video-clips-info), convert to readable format
                            elif isinstance(content, dict):
                                # You can format this however you want
                                # Option 1: Just stringify it
                                content_parts.append(json.dumps(content, indent=2))
                                
                                # Option 2: Extract video clip info nicely (uncomment to use)
                                # if 'video_clips' in content:
                                #     for clip in content['video_clips']:
                                #         clip_text = f"[{clip['video_clip_start_time']}s-{clip['video_clip_end_time']}s]: {clip['video_clip_info']}"
                                #         content_parts.append(clip_text)

                    if content_parts:
                        roast_content = '\n\n'.join(content_parts)
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, use the raw string as-is
                pass

        # Convert Markdown roast text to HTML for display
        html_result = simple_markdown_to_html(roast_content)
        return jsonify({"success": True, "result": html_result})

    # No chat_response; decide best fallback.
    fallback = system_msg or api_error
    if not fallback:
        fallback = "Unknown error: chat_response missing."
    return jsonify({"success": False, "error": fallback})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8111)


# video processing  - only english, cannot process other lan
# 