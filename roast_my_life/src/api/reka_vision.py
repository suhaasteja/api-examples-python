from typing import Dict, Any, List
import requests
from src.config import Config


def call_video_qa(video_id: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Call the Reka Video QA API for a given video.

    Parameters:
        video_id (str): The UUID of the video to query.
        messages (List[Dict[str, str]]): List of message objects with 'role' and 'content'.

    Returns:
        Dict[str, Any]: Parsed JSON response
    """
    headers = {
        "Content-Type": "application/json"
    }
    if Config.API_KEY:
        headers['X-Api-Key'] = Config.API_KEY

    payload = {
        "video_id": video_id,
        "messages": messages
    }

    if not Config.REKA_VIDEO_QA_ENDPOINT:
        return {"error": "No endpoint configured", "_status_code": 0, "_ok": False}
    
    try:
        resp = requests.post(
            Config.REKA_VIDEO_QA_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        try:
            data = resp.json()
        except Exception as e:
            print(f"JSON parse error: {e}")
            data = {"error": f"Non-JSON response (status {resp.status_code})"}

        # Add HTTP status info to response
        data['_status_code'] = resp.status_code
        data['_ok'] = resp.ok
        
        if not resp.ok and 'error' not in data:
            data['error'] = f"HTTP {resp.status_code} calling chat endpoint"
        return data
    except requests.Timeout:
        return {"error": "Request to chat API timed out"}
    except Exception as e:
        return {"error": f"Chat API call failed: {e}"}


def upload_video(video_name: str, video_url: str) -> Dict[str, Any]:
    """
    Upload a new video to the Reka Vision API.

    Args:
        video_name (str): Name for the video
        video_url (str): URL of the video to upload

    Returns:
        Dict[str, Any]: Response with success status and video_id or error
    """
    if not Config.API_KEY:
        return {"success": False, "error": "API key not configured"}

    try:
        response = requests.post(
            f"{Config.BASE_URL.rstrip('/')}/videos/upload",
            headers={
                "X-Api-Key": Config.API_KEY
            },
            data={
                'video_name': video_name,
                'index': 'true',
                'video_url': video_url
            },
            timeout=30
        )
        
        try:
            response_data = response.json()
        except Exception:
            response_data = {}

        if response.ok:
            video_id = response_data.get('video_id', 'unknown')
            return {
                "success": True, 
                "video_id": video_id,
                "message": "Video uploaded successfully"
            }
        else:
            error_msg = response_data.get('error') or response_data.get('message') or f"HTTP {response.status_code}"
            return {"success": False, "error": f"Upload failed: {error_msg}"}

    except requests.Timeout:
        return {"success": False, "error": "Request timed out"}
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {str(e)}"}
