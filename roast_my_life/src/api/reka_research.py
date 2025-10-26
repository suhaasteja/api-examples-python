from openai import OpenAI
from src.config import Config


def research_phrase(prompt: str, timeout: int = 90) -> str:
    """
    Use Reka Research API to research a phrase or claim.
    
    Args:
        prompt (str): Research prompt
        timeout (int): Request timeout in seconds
        
    Returns:
        str: Research results as markdown text
    """
    client = OpenAI(
        base_url=Config.REKA_RESEARCH_BASE_URL,
        api_key=Config.API_KEY
    )
    
    completion = client.chat.completions.create(
        model="reka-flash-research",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        timeout=timeout
    )
    
    return completion.choices[0].message.content
