from fastapi import APIRouter
from app.api.v1.endpoints import analytics, applications, auth, companies, matching

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(matching.router)
api_router.include_router(applications.router)
api_router.include_router(analytics.router)
