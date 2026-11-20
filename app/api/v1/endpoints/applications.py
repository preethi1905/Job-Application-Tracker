from datetime import date
import math
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.application import Application, ApplicationStatus
from app.models.company import Company
from app.models.status_history import StatusHistory
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationResponse,
    ApplicationUpdate,
    PaginatedApplications,
    StatusHistoryResponse,
)

router = APIRouter(prefix="/applications", tags=["Job Applications"])


@router.get(
    "",
    response_model=PaginatedApplications,
    summary="List applications with filtering, search and pagination",
    description=(
        "Retrieve job applications for the current user. Supports filtering by status, "
        "company ID, application date range, keyword search across title/company, "
        "and pagination."
    ),
)
def list_applications(
    status: Optional[ApplicationStatus] = Query(None, description="Filter by status (Applied, Interview, Offer, Rejected)"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    search: Optional[str] = Query(None, description="Search keyword in job title or company name"),
    date_from: Optional[date] = Query(None, description="Filter applied_date >= date_from"),
    date_to: Optional[date] = Query(None, description="Filter applied_date <= date_to"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = (
        db.query(Application)
        .outerjoin(Company, Application.company_id == Company.id)
        .filter(Application.user_id == current_user.id)
        .options(joinedload(Application.company))
    )

    if status:
        query = query.filter(Application.status == status)

    if company_id:
        query = query.filter(Application.company_id == company_id)

    if date_from:
        query = query.filter(Application.applied_date >= date_from)

    if date_to:
        query = query.filter(Application.applied_date <= date_to)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Application.job_title.ilike(search_filter))
            | (Company.name.ilike(search_filter))
            | (Application.location.ilike(search_filter))
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    items = (
        query.order_by(Application.applied_date.desc(), Application.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PaginatedApplications(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.post(
    "",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job application",
    description="Registers an application and logs the initial status to status_history.",
)
def create_application(
    app_in: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    # Resolve or create company if company_name provided and company_id is None
    company_id = app_in.company_id
    if not company_id and app_in.company_name:
        company_name_clean = app_in.company_name.strip()
        existing_company = (
            db.query(Company)
            .filter(Company.name.ilike(company_name_clean))
            .first()
        )
        if existing_company:
            company_id = existing_company.id
        else:
            new_company = Company(name=company_name_clean)
            db.add(new_company)
            db.flush()
            company_id = new_company.id

    # Verify company exists if specified
    if company_id:
        comp = db.query(Company).filter(Company.id == company_id).first()
        if not comp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {company_id} does not exist.",
            )

    applied_date = app_in.applied_date or date.today()

    application = Application(
        user_id=current_user.id,
        company_id=company_id,
        job_title=app_in.job_title.strip(),
        job_description=app_in.job_description,
        status=app_in.status,
        location=app_in.location,
        salary_min=app_in.salary_min,
        salary_max=app_in.salary_max,
        currency=app_in.currency,
        job_url=app_in.job_url,
        notes=app_in.notes,
        applied_date=applied_date,
    )
    db.add(application)
    db.flush()

    # Record initial status in status_history
    history = StatusHistory(
        application_id=application.id,
        old_status=None,
        new_status=application.status.value,
        notes=app_in.status_notes or f"Application submitted with status: {application.status.value}",
    )
    db.add(history)
    db.commit()
    db.refresh(application)
    return application


@router.get(
    "/{id}",
    response_model=ApplicationDetailResponse,
    summary="Get application details by ID",
)
def get_application(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    application = (
        db.query(Application)
        .filter(Application.id == id, Application.user_id == current_user.id)
        .options(
            joinedload(Application.company),
            joinedload(Application.status_history),
        )
        .first()
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {id} not found.",
        )
    return application


@router.put(
    "/{id}",
    response_model=ApplicationDetailResponse,
    summary="Update application details and status",
    description="Updates application fields. If the status changed, an entry is added to status_history.",
)
def update_application(
    id: int,
    app_in: ApplicationUpdate,
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

    if app_in.company_id is not None:
        comp = db.query(Company).filter(Company.id == app_in.company_id).first()
        if not comp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {app_in.company_id} does not exist.",
            )
        application.company_id = app_in.company_id

    if app_in.job_title is not None:
        application.job_title = app_in.job_title.strip()
    if app_in.job_description is not None:
        application.job_description = app_in.job_description
    if app_in.location is not None:
        application.location = app_in.location
    if app_in.salary_min is not None:
        application.salary_min = app_in.salary_min
    if app_in.salary_max is not None:
        application.salary_max = app_in.salary_max
    if app_in.currency is not None:
        application.currency = app_in.currency
    if app_in.job_url is not None:
        application.job_url = app_in.job_url
    if app_in.notes is not None:
        application.notes = app_in.notes
    if app_in.applied_date is not None:
        application.applied_date = app_in.applied_date

    # Status transition check
    if app_in.status is not None and app_in.status != application.status:
        old_status_val = application.status.value
        new_status_val = app_in.status.value
        application.status = app_in.status

        # Create history record
        history = StatusHistory(
            application_id=application.id,
            old_status=old_status_val,
            new_status=new_status_val,
            notes=app_in.status_notes or f"Status transitioned from {old_status_val} to {new_status_val}",
        )
        db.add(history)

    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an application",
)
def delete_application(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
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
    db.delete(application)
    db.commit()
    return None


@router.get(
    "/{id}/history",
    response_model=List[StatusHistoryResponse],
    summary="Get status transition timeline for an application",
)
def get_application_history(
    id: int,
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
    history = (
        db.query(StatusHistory)
        .filter(StatusHistory.application_id == id)
        .order_by(StatusHistory.changed_at.desc(), StatusHistory.id.desc())
        .all()
    )
    return history
