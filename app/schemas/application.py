from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.application import ApplicationStatus
from app.schemas.company import CompanyResponse


class StatusHistoryResponse(BaseModel):
    id: int
    application_id: int
    old_status: Optional[str] = None
    new_status: str
    notes: Optional[str] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationBase(BaseModel):
    job_title: str = Field(..., min_length=1, max_length=150)
    company_id: Optional[int] = Field(None, description="Existing company ID or create one")
    company_name: Optional[str] = Field(None, description="Convenience field to create/assign company by name")
    job_description: Optional[str] = Field(None, description="Full job description text")
    status: ApplicationStatus = Field(default=ApplicationStatus.APPLIED)
    location: Optional[str] = Field(None, max_length=150)
    salary_min: Optional[Decimal] = Field(None, ge=0)
    salary_max: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=10)
    job_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    applied_date: Optional[date] = None


class ApplicationCreate(ApplicationBase):
    status_notes: Optional[str] = Field(None, description="Optional note for the initial status history entry")


class ApplicationUpdate(BaseModel):
    job_title: Optional[str] = Field(None, min_length=1, max_length=150)
    company_id: Optional[int] = None
    job_description: Optional[str] = None
    status: Optional[ApplicationStatus] = None
    location: Optional[str] = Field(None, max_length=150)
    salary_min: Optional[Decimal] = Field(None, ge=0)
    salary_max: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    job_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    applied_date: Optional[date] = None
    status_notes: Optional[str] = Field(None, description="Note logged in status history if status changes")


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    company_id: Optional[int] = None
    job_title: str
    job_description: Optional[str] = None
    status: ApplicationStatus
    location: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    currency: str
    job_url: Optional[str] = None
    notes: Optional[str] = None
    applied_date: date
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanyResponse] = None

    model_config = ConfigDict(from_attributes=True)



class ApplicationDetailResponse(ApplicationResponse):
    status_history: List[StatusHistoryResponse] = []


class PaginatedApplications(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ApplicationResponse]
