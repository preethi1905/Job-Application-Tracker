from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsOverview
from app.services.analytics_service import get_user_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "",
    response_model=AnalyticsOverview,
    summary="Get application analytics and weekly response metrics",
    description=(
        "Executes SQL aggregations to calculate application distribution by status, "
        "overall candidate response rate, interview conversion rates, and weekly submission "
        "velocity and response trends."
    ),
)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    return get_user_analytics(db=db, user_id=current_user.id)
