from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    job_description: Optional[str] = Field(
        None,
        description="Job description text to compare against. If omitted, uses the application's saved job description.",
    )
    resume_text: Optional[str] = Field(
        None,
        description="Resume text to evaluate. If omitted, uses the current user's profile resume.",
    )


class CategoryScore(BaseModel):
    category: str
    matched: List[str]
    missing: List[str]
    score: float


class MatchSuggestion(BaseModel):
    type: str  # "missing_critical_skill", "action_verbs", "quantifiable_metrics", "formatting"
    severity: str  # "high", "medium", "low"
    message: str
    actionable_tip: str


class MatchResponse(BaseModel):
    application_id: int
    job_title: str
    match_score: float = Field(..., ge=0.0, le=100.0, description="Overall match percentage (0-100)")
    rating: str
    summary: str
    total_jd_keywords: int
    matched_keywords_count: int
    missing_keywords_count: int
    matching_keywords: List[str]
    missing_keywords: List[str]
    category_scores: List[CategoryScore]
    suggestions: List[MatchSuggestion]
    engine: str = "Heuristic-NLP-Matcher"
