from flask import Blueprint, request, jsonify, render_template
from typing import Dict, Any
from src.api.reka_vision import call_video_qa
from src.services.video_service import fetch_videos, transform_videos_for_template
from src.services.analysis_service import parse_structured_chat_response, format_chat_response_to_html
from src.services.markdown_service import markdown_to_html
from src.config import Config

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat/<video_id>')
def chat_page(video_id: str) -> str:
    """
    Render the chat interface for a specific video.
    
    Args:
        video_id: UUID of the video to chat about
        
    Returns:
        str: Rendered HTML template for the chat page
    """
    videos = fetch_videos()
    template_videos = transform_videos_for_template(videos)
    
    # Find the video
    video = None
    for v in template_videos:
        if v.get("id") == video_id:
            video = v
            break
    
    if not video:
        return "Video not found", 404
    
    return render_template('chat.html', video=video)


@chat_bp.route('/api/chat', methods=['POST'])
def chat_with_video() -> Dict[str, Any]:
    """
    Chat with a video using the Reka Video QA API as a language tutor.
    """
    data = request.get_json() or {}
    video_id = data.get('video_id')
    user_message = data.get('message', '').strip()
    conversation_history = data.get('conversation_history', [])
    current_timestamp = data.get('current_timestamp')  # Get video timestamp if provided
    
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
            "content": Config.LANGUAGE_TUTOR_SYSTEM_PROMPT
        })
    
    # Add previous conversation messages
    for msg in conversation_history:
        messages.append({
            "role": msg.get("role"),
            "content": msg.get("content")
        })
    
    # Add current user message with timestamp context if available
    user_content = user_message
    if current_timestamp is not None:
        mins = current_timestamp // 60
        secs = current_timestamp % 60
        time_str = f"{mins}:{secs:02d}"
        user_content = f"{user_message}\n\n[Context: User is asking about the video at timestamp {time_str} ({current_timestamp}s)]"
    
    messages.append({
        "role": "user",
        "content": user_content
    })
    
    try:
        response_data = call_video_qa(video_id, messages)
        
        status_code = response_data.get('_status_code', 0)
        is_ok = response_data.get('_ok', False)
        
        if not is_ok:
            error_msg = response_data.get('error') or f"HTTP {status_code}"
            return jsonify({"error": f"API error: {error_msg}"}), status_code if status_code >= 400 else 500
        
        chat_response = response_data.get('chat_response')
        system_message = response_data.get('system_message')
        status = response_data.get('status')
        
        if status and status != 'success':
            print(f"Status check failed: {status}")
            return jsonify({"error": f"API status: {status}"}), 500
        
        if chat_response:
            # Parse structured response to extract content
            response_text = parse_structured_chat_response(chat_response)
            
            # Convert markdown to HTML for display
            html_response = markdown_to_html(response_text)
            
            return jsonify({
                "success": True, 
                "response": html_response,
                "raw_response": response_text
            })
        
        elif system_message:
            html_response = markdown_to_html(system_message)
            return jsonify({
                "success": True,
                "response": html_response,
                "raw_response": system_message
            })
        
        else:
            return jsonify({"error": f"No response content. Status: {status}"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Chat failed: {str(e)}"}), 500
