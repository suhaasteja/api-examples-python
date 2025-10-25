import os
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
import requests

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


def call_reka_vision_qa(video_id: str) -> Dict[str, Any]:
    """Call the Reka Video QA API for a given video.

    The request format follows the user's provided specification. We issue a
    POST request with the video_id and a static user prompt asking to gently
    roast the person in the video.

    Environment Variables:
        REKA_VIDEO_QA_ENDPOINT: Optional override for the API endpoint.
        api_key or API_KEY: API key placed in the X-Api-Key header.

    Parameters:
        video_id (str): The UUID of the video to query.

    Returns:
        Dict[str, Any]: Parsed JSON response (may include keys like
        chat_response, system_message, error, status, etc.). On total failure
        returns a dict with an 'error' key.
    """
    headers = {}
    if api_key:
        headers['X-Api-Key'] = api_key

    payload = {
        "video_id": video_id,
        "messages": [
            {
                "role": "user",
                "content": "at 2:50s what is the conversation about. return the whole transcript for the 5 seconds before to understand the context"
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
        # Even on non-2xx we attempt to parse JSON for richer error context.
        data: Dict[str, Any]
        try:
            data = resp.json()
        except Exception:
            data = {"error": f"Non-JSON response (status {resp.status_code})"}

        if not resp.ok and 'error' not in data:
            data['error'] = f"HTTP {resp.status_code} calling chat endpoint"
        return data
    except requests.Timeout:
        return {"error": "Request to chat API timed out"}
    except Exception as e:  # broad catch to avoid propagating unexpected errors
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


@app.route('/api/chat', methods=['POST'])
def chat_with_video() -> Dict[str, Any]:
    """
    Chat with a video using the Reka Video QA API.
    Follows documentation from: https://docs.reka.ai/video-qa
    
    Expects JSON body: { 
        "video_id": "uuid",
        "message": "user's question",
        "conversation_history": [] // optional, list of previous messages
    }
    
    Returns:
        Dict[str, Any]: JSON response with fields:
            success (bool)
            response (str) - the AI's response
            error (str) when not successful
    """
    data = request.get_json() or {}
    video_id = data.get('video_id')
    user_message = data.get('message', '').strip()
    conversation_history = data.get('conversation_history', [])
    
    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    # Build messages array following documentation format
    messages = []
    
    # Add previous conversation messages
    # Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
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
    
    # Call Reka Video QA API following documentation
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Payload following documentation structure
    payload = {
        "video_id": video_id,
        "messages": messages
    }
    
    try:
        resp = requests.post(
            REKA_VIDEO_QA_ENDPOINT,  # Uses /qa/chat endpoint
            headers=headers,
            json=payload,
            timeout=60
        )
        
        # Parse response
        try:
            response_data = resp.json()
        except Exception:
            response_data = {"error": f"Non-JSON response (status {resp.status_code})"}
        
        if resp.ok:
            # According to docs, response contains "answer" field
            answer = response_data.get('answer')
            
            # Fallback to other possible field names for compatibility
            if not answer:
                answer = response_data.get('chat_response')
            
            if answer:
                response_text = answer
                
                # Handle structured JSON response if present
                if isinstance(answer, str) and answer.strip().startswith('{'):
                    try:
                        import json
                        parsed = json.loads(answer)
                        
                        # Check if it's the sections format
                        if isinstance(parsed, dict) and 'sections' in parsed:
                            sections = parsed.get('sections', [])
                            content_parts = []
                            
                            for section in sections:
                                if isinstance(section, dict) and 'section_content' in section:
                                    content = section['section_content']
                                    
                                    # Handle markdown sections
                                    if isinstance(content, str):
                                        content_parts.append(content)
                                    
                                    # Handle video clips sections
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
                        # Not JSON or parsing failed, use as-is
                        pass
                
                # Convert markdown to HTML
                html_response = simple_markdown_to_html(response_text)
                
                return jsonify({
                    "success": True, 
                    "response": html_response,
                    "raw_response": response_text,
                    "confidence": response_data.get('confidence'),  # Include confidence if available
                    "timestamp": response_data.get('timestamp')     # Include timestamp if available
                })
            
            # No answer field found
            return jsonify({
                "error": f"No answer in response. Available fields: {list(response_data.keys())}"
            }), 500
            
        else:
            # Error response
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
