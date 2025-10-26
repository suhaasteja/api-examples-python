from flask import Blueprint, request, jsonify
from typing import Dict, Any
import traceback
from src.api.reka_vision import call_video_qa
from src.api.reka_research import research_phrase
from src.services.analysis_service import (
    parse_video_analysis_response,
    parse_structured_chat_response,
    build_analysis_prompt,
    build_phrase_exploration_prompts
)
from src.services.markdown_service import markdown_to_html

language_bp = Blueprint('language', __name__)


@language_bp.route('/api/analyze_video', methods=['POST'])
def analyze_video() -> Dict[str, Any]:
    """
    Automatically analyze a video to extract interesting phrases and facts.
    """
    data = request.get_json() or {}
    video_id = data.get('video_id')
    
    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400
    
    try:
        analysis_prompt = build_analysis_prompt()
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert at analyzing video content. Always respond with valid JSON only, no additional text or formatting."
            },
            {
                "role": "user",
                "content": analysis_prompt
            }
        ]
        
        print(f"Analyzing video: {video_id}")
        
        response_data = call_video_qa(video_id, messages)
        
        status_code = response_data.get('_status_code', 0)
        is_ok = response_data.get('_ok', False)
        print(f"Response status: {status_code}")
        
        if is_ok:
            chat_response = response_data.get('chat_response')
            
            if not chat_response:
                print("No chat_response in data")
                return jsonify({
                    "success": True,
                    "primary_language": "Unknown",
                    "video_topic": "Analysis unavailable",
                    "items": []
                })
            
            print(f"Chat response preview: {str(chat_response)[:200]}")
            
            result = parse_video_analysis_response(chat_response)
            print(f"Successfully extracted {len(result.get('items', []))} items")
            
            return jsonify(result)
        else:
            error_msg = response_data.get('error') or f"HTTP {status_code}"
            print(f"API error: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"Analysis failed: {error_msg}"
            }), status_code if status_code >= 400 else 500
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }), 500


@language_bp.route('/api/explore_phrase', methods=['POST'])
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
        
        video_prompt, research_prompt = build_phrase_exploration_prompts(
            phrase, timestamp, context, category
        )
        
        video_messages = [
            {
                "role": "user",
                "content": video_prompt
            }
        ]
        
        video_data = call_video_qa(video_id, video_messages)
        
        # Check if video QA succeeded
        if video_data.get('_ok', False):
            video_context = video_data.get('chat_response', 'Could not retrieve video context')
        else:
            return jsonify({
                "success": False,
                "error": "Video QA failed"
            }), 500
        
        # Parse structured response if present
        video_context = parse_structured_chat_response(video_context)
        
        print(f"Video context retrieved: {len(str(video_context))} chars")
        
        # STEP 2: Research additional information using Reka Research
        print(f"Step 2: Researching '{phrase}' on the web")
        
        web_research = research_phrase(research_prompt)
        
        print(f"Web research retrieved: {len(str(web_research))} chars")
        
        # STEP 3: Combine both contexts into a comprehensive response
        combined_response = f"""## 📹 From the Video

{video_context}

---

## 🌐 Additional Research

{web_research}"""

        # Convert to HTML
        html_response = markdown_to_html(combined_response)
        
        return jsonify({
            "success": True,
            "response": html_response,
            "raw_response": combined_response,
            "video_context": str(video_context),
            "web_research": str(web_research)
        })
        
    except Exception as e:
        print(f"Error in explore_phrase: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": f"Failed to explore phrase: {str(e)}"
        }), 500
