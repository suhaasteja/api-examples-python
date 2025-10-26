from pydantic import BaseModel, Field
from typing import List, Literal


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
