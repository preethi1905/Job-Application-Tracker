from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel


class StatusCountItem(BaseModel):
    status: str
    count: int
    percentage: float


class WeeklyResponseMetric(BaseModel):
    week_start: str
    applications_submitted: int
    interviews_scheduled: int
    offers_received: int
    rejections_received: int
    weekly_response_rate: float


class AnalyticsOverview(BaseModel):
    total_applications: int
    active_applications: int
    status_breakdown: List[StatusCountItem]
    overall_response_rate: float
    interview_conversion_rate: float
    offer_conversion_rate: float
    weekly_trends: List[WeeklyResponseMetric]
