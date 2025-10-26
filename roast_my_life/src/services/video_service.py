import time
from typing import Any, Dict, List
import requests
from src.config import Config


# Simple in-memory cache for videos to avoid hitting the API on every request.
_VIDEO_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "ttl": Config.VIDEO_CACHE_TTL,
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

    if not Config.BASE_URL:
        # Without BASE_URL we can't call the API; return empty.
        return []

    if not is_stale and _VIDEO_CACHE["results"]:
        return _VIDEO_CACHE["results"]

    url = f"{Config.BASE_URL.rstrip('/')}/videos/get"
    headers = {}
    if Config.API_KEY:
        headers["X-Api-Key"] = Config.API_KEY

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


def invalidate_video_cache() -> None:
    """Invalidate the video cache to force a refresh on next fetch."""
    _VIDEO_CACHE["timestamp"] = 0.0


def transform_videos_for_template(videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform videos to a simplified structure for templates.
    
    Args:
        videos: Raw video data from API
        
    Returns:
        List of simplified video dictionaries
    """
    template_videos = []
    for v in videos:
        meta = v.get("metadata", {})
        template_videos.append({
            "id": v.get("video_id"),
            "name": meta.get("title") or meta.get("video_name") or "Untitled",
            "thumbnail": meta.get("thumbnail") or "/static/images/image1.jpg",
            "url": v.get("url") or meta.get("url") or "",
            "video_url": v.get("url") or meta.get("url") or "",
        })
    return template_videos
