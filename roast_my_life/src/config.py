import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # API Configuration
    API_KEY = os.environ.get('API_KEY')
    BASE_URL = os.environ.get('BASE_URL')
    
    # Reka API Endpoints
    REKA_VIDEO_QA_ENDPOINT = os.environ.get(
        'REKA_VIDEO_QA_ENDPOINT',
        f"{BASE_URL.rstrip('/') if BASE_URL else ''}/qa/chat"
    )
    REKA_RESEARCH_BASE_URL = "https://api.reka.ai/v1"
    
    # Cache Configuration
    VIDEO_CACHE_TTL = 60.0  # seconds
    
    # Flask Configuration
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8111))
    
    # Language Tutor System Prompt
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
- **IMPORTANT**: Always provide English translations in brackets for any non-English phrases, words, or expressions. Format: "[Original Text] (English: translation)"

Keep your tone friendly, educational, and motivating. Focus on practical learning that helps the student improve their comprehension and speaking skills."""
