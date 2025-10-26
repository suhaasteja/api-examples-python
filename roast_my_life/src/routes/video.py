from flask import Blueprint, request, jsonify
from typing import Dict, Any
from src.api.reka_vision import upload_video
from src.services.video_service import invalidate_video_cache

video_bp = Blueprint('video', __name__)


@video_bp.route('/api/upload_video', methods=['POST'])
def upload_video_route() -> Dict[str, Any]:
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

    result = upload_video(video_name, video_url)
    
    if result.get('success'):
        # Invalidate cache to force refresh
        invalidate_video_cache()
        return jsonify(result)
    else:
        return jsonify(result), 500
