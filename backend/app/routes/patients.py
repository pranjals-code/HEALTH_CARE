"""
Patient microservice routes (placeholder for future expansion)
Currently minimal - will expand in separate microservice
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID
from app.database import get_db
from app.models.auth import User
from app.core.dependencies import get_current_user, require_role
from app.services.search_service import (
    SearchUnavailableError,
    search_patients as run_patient_search,
)

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


# TODO: Implement patient microservice routes
# This will be a separate microservice in production
# For now, placeholder endpoints


@router.get("/")
async def list_patients(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role("DOCTOR")),
):
    """
    List patients (DOCTOR, NURSE, etc.)
    Future: Will be in separate Patient Microservice
    """
    return {
        "message": "Patient listing - coming soon in patient microservice",
        "status": "not_implemented",
    }


@router.get("/search")
async def search_patients(
    q: str = Query(..., min_length=2, description="Patient search query"),
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_role("DOCTOR")),
):
    """
    Search indexed patients through Elasticsearch.
    """
    del db  # dependency kept for auth/session consistency

    organization_id = None
    if current_user.staff_profile:
        organization_id = current_user.staff_profile.organization_id

    try:
        results = run_patient_search(
            query=q,
            organization_id=organization_id,
            size=limit,
        )
    except SearchUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Patient search unavailable: {exc}",
        ) from exc

    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.get("/{patient_id}")
async def get_patient(
    patient_id: UUID, db=Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get patient details
    Future: Will be in separate Patient Microservice
    """
    return {
        "message": "Patient details - coming soon in patient microservice",
        "status": "not_implemented",
        "patient_id": str(patient_id),
    }
