"""
Protected media upload routes using existing JWT auth.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from google.cloud import storage
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.media import Media

router = APIRouter(tags=["media"])
ALLOWED_EXTENSIONS = {"pdf", "docx", "mp4"}
BUCKET_NAME = "raw-video-bucket-12345"


def serialize_media(media: Media) -> dict:
    return {
        "id": media.id,
        "user_id": media.user_id,
        "file_name": media.file_name,
        "file_path": media.file_path,
        "uploaded_at": media.uploaded_at,
    }


def upload_to_gcs(file: UploadFile, user_id: str) -> str:
    file_name = Path(file.filename or "").name
    blob_path = f"{user_id}/{file_name}"

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)

    file.file.seek(0)
    blob.upload_from_file(file.file, content_type=file.content_type)
    file.file.seek(0)

    return f"gs://{BUCKET_NAME}/{blob_path}"


@router.post("/upload", response_model=None)
def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user_id = str(current_user.id)
    file_name = file.filename or ""
    extension = Path(file_name).suffix.lower().lstrip(".")

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pdf, docx, and mp4 files are allowed",
        )

    try:
        uploaded_file_path = upload_to_gcs(file, user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        ) from exc
    finally:
        file.file.close()

    media = Media(
        user_id=user_id,
        file_name=Path(file_name).name,
        file_path=uploaded_file_path,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return serialize_media(media)


@router.get("/my-uploads", response_model=None)
def get_my_uploads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    user_id = str(current_user.id)
    uploads = (
        db.query(Media)
        .filter(Media.user_id == user_id)
        .order_by(Media.uploaded_at.desc())
        .all()
    )
    return [serialize_media(upload) for upload in uploads]
