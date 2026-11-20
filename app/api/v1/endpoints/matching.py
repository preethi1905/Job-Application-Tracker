from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.application import Application
from app.models.user import User
from app.schemas.matching import MatchRequest, MatchResponse
from app.services.matching_service import compute_resume_match

router = APIRouter(prefix="/applications", tags=["AI Match Engine"])


@router.post(
    "/{id}/match",
    response_model=MatchResponse,
    summary="Score resume against job description and identify missing keywords",
    description=(
        "Scores candidate resume text against the target job description. "
        "Returns an overall ATS match score (0-100), matching keywords, missing keywords, "
        "category-specific competencies, and actionable tailoring suggestions."
    ),
)
def match_application(
    id: int,
    match_in: MatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    application = (
        db.query(Application)
        .filter(Application.id == id, Application.user_id == current_user.id)
        .first()
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {id} not found.",
        )

    # 1. Determine job description: request body -> application record -> fallback
    jd_text = (
        match_in.job_description
        or application.job_description
        or f"{application.job_title} role at target company."
    )

    # 2. Determine resume text: request body -> user's saved profile resume -> empty
    resume_text = match_in.resume_text or current_user.resume_text or ""

    if not resume_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No resume text provided. Please supply 'resume_text' in the request body "
                "or update your profile resume via PUT /api/v1/auth/me."
            ),
        )

    match_result = compute_resume_match(
        application_id=application.id,
        job_title=application.job_title,
        job_description=jd_text,
        resume_text=resume_text,
    )
    return match_result
