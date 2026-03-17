"""
Reindex patients from PostgreSQL into Elasticsearch.

Run from backend directory:
python -m app.scripts.reindex_patients
"""

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.auth import Patient, User
from app.services.search_service import (
    build_patient_document,
    ensure_patient_index,
    index_patient_document,
)


def reindex_patients() -> int:
    """Rebuild the patient search index from relational data."""
    ensure_patient_index()

    db: Session = SessionLocal()
    try:
        rows = db.query(Patient, User).outerjoin(User, Patient.user_id == User.id).all()

        for patient, user in rows:
            index_patient_document(build_patient_document(patient, user))

        return len(rows)
    finally:
        db.close()


if __name__ == "__main__":
    total = reindex_patients()
    print(f"Reindexed {total} patients into Elasticsearch.")
