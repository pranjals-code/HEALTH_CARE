"""
Main FastAPI application
Microservice Architecture: Auth/RBAC Service + OTP/SMS Auth + Patient Module (stub)
"""

import time
from fastapi import FastAPI
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from app.config import settings
from app.core.logger import configure_logging, get_logger
from app.database import engine
from app.models.media import Media
from app.monitoring import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    HTTP_RESPONSE_STATUS_TOTAL,
)
from app.routes import auth, otp_auth, patients, media
from app.services.search_service import ensure_patient_index

configure_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Healthcare System API",
    description="Production-grade Healthcare Information System - Auth Service with OTP/SMS Verification & Celery Background Tasks",
    version=settings.SERVICE_VERSION,
    docs_url="/docs",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_path_template(request: Request) -> str:
    """Return normalized route path for low-cardinality labels."""
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    return request.url.path


@app.middleware("http")
async def prometheus_http_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start_time
        method = request.method
        path = _get_path_template(request)
        status = str(status_code)

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            path=path,
            status_code=status,
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            path=path,
            status_code=status,
        ).observe(duration)

        HTTP_RESPONSE_STATUS_TOTAL.labels(
            path=path,
            status_code=status,
        ).inc()


# Include routers
app.include_router(auth.router)
app.include_router(otp_auth.router)  # OTP & Phone-based authentication
app.include_router(patients.router)
app.include_router(media.router)


@app.on_event("startup")
def startup_tasks() -> None:
    """Initialize optional external dependencies."""
    Media.__table__.create(bind=engine, checkfirst=True)

    try:
        ensure_patient_index()
        logger.info("Elasticsearch patient index is ready")
    except Exception as exc:
        logger.warning("Elasticsearch startup check failed: %s", exc)


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Root endpoint
@app.get("/")
def read_root():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "features": [
            "JWT Authentication",
            "Protected File Uploads",
            "User Upload Listing",
            "OTP/SMS Verification",
            "Phone-based Registration",
            "Password Reset via OTP",
            "Role-Based Access Control (RBAC)",
            "Background Task Processing (Celery)",
            "Patient Management",
        ],
        "api_docs": "/api/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "features_enabled": {
            "jwt": True,
            "otp_sms": True,
            "rbac": True,
            "celery_tasks": True,
        },
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI service on 0.0.0.0:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
