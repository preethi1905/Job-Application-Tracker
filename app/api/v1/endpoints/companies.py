from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get(
    "",
    response_model=List[CompanyResponse],
    summary="List all companies",
    description="Retrieve companies with optional name search and pagination.",
)
def list_companies(
    search: Optional[str] = Query(None, description="Search companies by name or industry"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Any:
    query = db.query(Company)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Company.name.ilike(search_filter)) | (Company.industry.ilike(search_filter))
        )
    companies = query.order_by(Company.name.asc()).offset(skip).limit(limit).all()
    return companies


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company",
)
def create_company(
    company_in: CompanyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Any:
    existing = db.query(Company).filter(Company.name.ilike(company_in.name)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company '{company_in.name}' already exists with ID {existing.id}.",
        )
    company = Company(
        name=company_in.name.strip(),
        website=company_in.website,
        location=company_in.location,
        industry=company_in.industry,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get(
    "/{id}",
    response_model=CompanyResponse,
    summary="Get company by ID",
)
def get_company(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Any:
    company = db.query(Company).filter(Company.id == id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {id} not found.",
        )
    return company


@router.put(
    "/{id}",
    response_model=CompanyResponse,
    summary="Update company details",
)
def update_company(
    id: int,
    company_in: CompanyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Any:
    company = db.query(Company).filter(Company.id == id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {id} not found.",
        )
    if company_in.name is not None:
        # Check uniqueness if name changed
        conflict = (
            db.query(Company)
            .filter(Company.name.ilike(company_in.name), Company.id != id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another company with name '{company_in.name}' already exists.",
            )
        company.name = company_in.name.strip()
    if company_in.website is not None:
        company.website = company_in.website
    if company_in.location is not None:
        company.location = company_in.location
    if company_in.industry is not None:
        company.industry = company_in.industry

    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
)
def delete_company(
    id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    company = db.query(Company).filter(Company.id == id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {id} not found.",
        )
    db.delete(company)
    db.commit()
    return None
