import json
import re
from typing import Dict, Any, List


def parse_video_analysis_response(chat_response: Any) -> Dict[str, Any]:
    """
    Parse the video analysis response from the API.
    
    Args:
        chat_response: Raw response from the API
        
    Returns:
        Dict with success, primary_language, video_topic, and items
    """
    try:
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
        
        return {
            "success": True,
            "primary_language": primary_language,
            "video_topic": video_topic,
            "items": cleaned_items
        }
        
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        # Return success with empty items on parse error
        return {
            "success": True,
            "primary_language": "Unknown",
            "video_topic": "Could not analyze video",
            "items": [],
            "parse_error": str(e)
        }


def parse_structured_chat_response(chat_response: Any) -> str:
    """
    Parse structured JSON chat response and extract content.
    
    Args:
        chat_response: Response from chat API
        
    Returns:
        Extracted text content
    """
    if isinstance(chat_response, str):
        try:
            # Remove markdown code blocks if present
            chat_str = chat_response.strip()
            chat_str = re.sub(r'```json\s*', '', chat_str)
            chat_str = re.sub(r'```\s*$', '', chat_str)
            chat_str = chat_str.strip()
            
            # Try to parse as JSON
            if chat_str.startswith('{'):
                parsed = json.loads(chat_str)
                if isinstance(parsed, dict) and 'sections' in parsed:
                    content_parts = []
                    for section in parsed.get('sections', []):
                        if isinstance(section, dict) and 'section_content' in section:
                            content = section['section_content']
                            # Only add if it's a string (markdown sections)
                            if isinstance(content, str):
                                content_parts.append(content)
                            # For dict content (like video-clips-info), convert to readable format
                            elif isinstance(content, dict):
                                # Extract video clip info nicely
                                if 'video_clips' in content:
                                    for clip in content.get('video_clips', []):
                                        start = clip.get('video_clip_start_time', 0)
                                        end = clip.get('video_clip_end_time', 0)
                                        info = clip.get('video_clip_info', '')
                                        clip_text = f"**[{start}s-{end}s]**: {info}"
                                        content_parts.append(clip_text)
                                else:
                                    # Fallback: stringify the dict
                                    content_parts.append(json.dumps(content, indent=2))
                    
                    if content_parts:
                        return '\n\n'.join(content_parts)
        except (json.JSONDecodeError, ValueError):
            # If parsing fails, return as-is
            pass
    
    return str(chat_response)


def build_analysis_prompt() -> str:
    """
    Build the prompt for automatic video analysis.
    
    Returns:
        Analysis prompt string
    """
    return """Analyze this video and identify interesting content for language learning and fact verification.

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
1. The exact phrase or claim IN THE ORIGINAL LANGUAGE, followed by English translation in parentheses
2. Timestamp in seconds where it appears
3. Brief context
4. Category (language_learning or fact_check)
5. Why it's interesting

IMPORTANT: 
- For non-English phrases, ALWAYS include English translation. Format: "[Original phrase] (English: translation)"
- Return ONLY valid JSON (no markdown, no code blocks)

JSON format:
{
  "primary_language": "detected language name",
  "video_topic": "brief description of video content",
  "items": [
    {
      "phrase": "[Original phrase] (English: translation)",
      "timestamp": 120,
      "context": "what's happening in this moment",
      "category": "language_learning",
      "reason": "why this is interesting to learn",
      "language": "language name"
    }
  ]
}"""


def build_phrase_exploration_prompts(phrase: str, timestamp: int, context: str, category: str) -> tuple[str, str]:
    """
    Build prompts for video context and web research.
    
    Args:
        phrase: The phrase to explore
        timestamp: Timestamp in seconds
        context: Brief context
        category: Category of the phrase
        
    Returns:
        Tuple of (video_prompt, research_prompt)
    """
    video_prompt = f"""Analyze this specific moment in the video at around {timestamp} seconds.

Focus on the phrase: "{phrase}"

Provide:
1. The exact context - what's happening when this is said
2. Who says it and why
3. The tone and emotion
4. Any visual context that's relevant
5. How this phrase fits into the conversation

Be detailed and specific."""

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
    else:
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

    return video_prompt, research_prompt


def format_chat_response_to_markdown(chat_response: Any) -> str:
    """
    Convert structured chat response with sections into markdown format.
    Handles both structured JSON with sections and plain text responses.
    
    Args:
        chat_response: Response from chat API (JSON string or dict)
        
    Returns:
        Markdown string
    """
    # Handle empty or None responses
    if not chat_response:
        return "No response received."
    
    # Start with the original response as default
    response_text = str(chat_response)
    
    # Try to parse and extract sections if it's structured JSON
    if isinstance(chat_response, str):
        if not chat_response.strip():
            return "Empty response received."
        
        # Only try to parse if it looks like JSON
        if chat_response.strip().startswith('{'):
            try:
                # Remove markdown code blocks if present
                chat_str = chat_response.strip()
                chat_str = re.sub(r'```json\s*', '', chat_str)
                chat_str = re.sub(r'```\s*$', '', chat_str)
                chat_str = chat_str.strip()
                
                parsed = json.loads(chat_str)
                
                # Check if it has sections structure
                if isinstance(parsed, dict) and 'sections' in parsed:
                    content_parts = []
                    
                    for section in parsed.get('sections', []):
                        if not isinstance(section, dict) or 'section_content' not in section:
                            continue
                        
                        content = section['section_content']
                        
                        # Handle string content (markdown)
                        if isinstance(content, str):
                            content_parts.append(content)
                        
                        # Handle dict content (video clips)
                        elif isinstance(content, dict) and 'video_clips' in content:
                            clips_markdown = []
                            for clip in content['video_clips']:
                                start = clip.get('video_clip_start_time', 0)
                                end = clip.get('video_clip_end_time', 0)
                                info = clip.get('video_clip_info', '')
                                clips_markdown.append(f"**⏱️ [{start}s - {end}s]**: {info}")
                            
                            if clips_markdown:
                                content_parts.append('\n\n'.join(clips_markdown))
                    
                    # Only replace response_text if we successfully extracted content
                    if content_parts:
                        response_text = '\n\n'.join(content_parts)
                
            except (json.JSONDecodeError, ValueError) as e:
                # If parsing fails, keep the original response_text
                print(f"JSON decode error (using original response): {e}")
                pass
    
    return response_text


def format_chat_response_to_html(chat_response: Any) -> str:
    """
    Format structured chat response with sections into proper HTML.
    
    Args:
        chat_response: Response from chat API (JSON string or dict)
        
    Returns:
        Formatted HTML string
    """
    try:
        # Convert to markdown first, then to HTML
        markdown_content = format_chat_response_to_markdown(chat_response)
        
        # Use existing markdown to HTML converter
        from src.services.markdown_service import markdown_to_html
        return markdown_to_html(markdown_content)
        
    except Exception as e:
        print(f"Error formatting chat response: {e}")
        return str(chat_response)


def format_time(seconds: float) -> str:
    """
    Convert seconds to MM:SS format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"
