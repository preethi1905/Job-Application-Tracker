from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func, case, cast, Date
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.status_history import StatusHistory
from app.schemas.analytics import (
    AnalyticsOverview,
    StatusCountItem,
    WeeklyResponseMetric,
)


def get_user_analytics(db: Session, user_id: int) -> AnalyticsOverview:
    """
    Computes SQL aggregations for:
    1. Applications grouped by status (count + percentages)
    2. Overall response rate and stage conversion rates
    3. Weekly submission velocity and response rates using date grouping
    """
    # 1. Total applications count
    total_apps = (
        db.query(func.count(Application.id))
        .filter(Application.user_id == user_id)
        .scalar()
        or 0
    )

    if total_apps == 0:
        return AnalyticsOverview(
            total_applications=0,
            active_applications=0,
            status_breakdown=[],
            overall_response_rate=0.0,
            interview_conversion_rate=0.0,
            offer_conversion_rate=0.0,
            weekly_trends=[],
        )

    # 2. Aggregation: Applications per status
    status_counts_raw = (
        db.query(Application.status, func.count(Application.id).label("count"))
        .filter(Application.user_id == user_id)
        .group_by(Application.status)
        .all()
    )

    status_dict = {
        ApplicationStatus.APPLIED.value: 0,
        ApplicationStatus.INTERVIEW.value: 0,
        ApplicationStatus.OFFER.value: 0,
        ApplicationStatus.REJECTED.value: 0,
    }

    for status_val, count in status_counts_raw:
        # Handles both Enum object or string value
        key = status_val.value if hasattr(status_val, "value") else str(status_val)
        status_dict[key] = count

    breakdown: List[StatusCountItem] = []
    for status_name, count in status_dict.items():
        pct = round((count / total_apps) * 100, 1) if total_apps > 0 else 0.0
        breakdown.append(
            StatusCountItem(
                status=status_name,
                count=count,
                percentage=pct,
            )
        )

    # Rates
    interviews = status_dict.get(ApplicationStatus.INTERVIEW.value, 0)
    offers = status_dict.get(ApplicationStatus.OFFER.value, 0)
    rejections = status_dict.get(ApplicationStatus.REJECTED.value, 0)
    
    # Active = Applied + Interview
    active_apps = status_dict.get(ApplicationStatus.APPLIED.value, 0) + interviews

    # Overall response rate: applications that progressed past Applied
    responded_apps = interviews + offers + rejections
    overall_response_rate = round((responded_apps / total_apps) * 100, 1) if total_apps > 0 else 0.0
    interview_conversion_rate = round((interviews / total_apps) * 100, 1) if total_apps > 0 else 0.0
    offer_conversion_rate = round((offers / total_apps) * 100, 1) if total_apps > 0 else 0.0

    # 3. Weekly Trends using SQL aggregation
    dialect = db.bind.dialect.name if db.bind else "sqlite"
    
    if dialect == "postgresql":
        week_col = func.to_char(func.date_trunc("week", Application.applied_date), "YYYY-MM-DD")
    else:
        # SQLite fallback: Year and Week format
        week_col = func.strftime("%Y-W%W", Application.applied_date)

    weekly_raw = (
        db.query(
            week_col.label("week_label"),
            func.count(Application.id).label("total_submitted"),
            func.sum(
                case(
                    (Application.status == ApplicationStatus.INTERVIEW, 1),
                    else_=0,
                )
            ).label("interviews"),
            func.sum(
                case(
                    (Application.status == ApplicationStatus.OFFER, 1),
                    else_=0,
                )
            ).label("offers"),
            func.sum(
                case(
                    (Application.status == ApplicationStatus.REJECTED, 1),
                    else_=0,
                )
            ).label("rejections"),
        )
        .filter(Application.user_id == user_id)
        .group_by("week_label")
        .order_by("week_label")
        .all()
    )

    weekly_trends: List[WeeklyResponseMetric] = []
    for row in weekly_raw:
        submitted = row.total_submitted or 0
        ints = row.interviews or 0
        ofs = row.offers or 0
        rejs = row.rejections or 0
        
        # Response rate for this cohort
        resps = ints + ofs + rejs
        rate = round((resps / submitted) * 100, 1) if submitted > 0 else 0.0
        
        weekly_trends.append(
            WeeklyResponseMetric(
                week_start=str(row.week_label),
                applications_submitted=submitted,
                interviews_scheduled=ints,
                offers_received=ofs,
                rejections_received=rejs,
                weekly_response_rate=rate,
            )
        )

    return AnalyticsOverview(
        total_applications=total_apps,
        active_applications=active_apps,
        status_breakdown=breakdown,
        overall_response_rate=overall_response_rate,
        interview_conversion_rate=interview_conversion_rate,
        offer_conversion_rate=offer_conversion_rate,
        weekly_trends=weekly_trends,
    )
