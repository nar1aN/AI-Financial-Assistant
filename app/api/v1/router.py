from fastapi import APIRouter
from app.api.v1.endpoints import upload

router = APIRouter()

router.include_router(upload.router, prefix="/upload", tags=["upload"])
# router.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
# router.include_router(report.router, prefix="/report", tags=["report"])
