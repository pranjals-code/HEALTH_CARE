"""
Elasticsearch helpers for patient search.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from elasticsearch import Elasticsearch
from app.config import settings
from app.core.logger import get_logger
from app.models.auth import Patient, User

logger = get_logger(__name__)


PATIENT_INDEX_MAPPING: Dict[str, Any] = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "organization_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "mrn": {"type": "keyword"},
            "first_name": {"type": "text"},
            "last_name": {"type": "text"},
            "full_name": {"type": "text"},
            "email": {"type": "text"},
            "phone": {"type": "text"},
            "date_of_birth": {"type": "keyword"},
            "gender": {"type": "keyword"},
            "is_active": {"type": "boolean"},
        }
    }
}


class SearchUnavailableError(RuntimeError):
    """Raised when Elasticsearch-backed search is unavailable."""


def get_es_client() -> Elasticsearch:
    """Create Elasticsearch client from app settings."""
    return Elasticsearch(
        settings.ELASTICSEARCH_URL,
        request_timeout=5,
        max_retries=0,
        retry_on_timeout=False,
    )


def ensure_patient_index() -> None:
    """Create patient index when missing."""
    if not settings.ELASTICSEARCH_ENABLED:
        logger.info("Elasticsearch is disabled; skipping patient index startup check")
        return

    client = get_es_client()
    if not client.indices.exists(index=settings.ELASTICSEARCH_PATIENT_INDEX):
        client.indices.create(
            index=settings.ELASTICSEARCH_PATIENT_INDEX,
            body=PATIENT_INDEX_MAPPING,
        )


def build_patient_document(patient: Patient, user: Optional[User]) -> Dict[str, Any]:
    """Flatten Patient and User into a searchable document."""
    first_name = user.first_name if user else ""
    last_name = user.last_name if user else ""
    return {
        "id": str(patient.id),
        "organization_id": str(patient.organization_id),
        "user_id": str(patient.user_id) if patient.user_id else None,
        "mrn": patient.mrn,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}".strip(),
        "email": user.email if user else "",
        "phone": user.phone if user and user.phone else "",
        "date_of_birth": patient.date_of_birth,
        "gender": patient.gender,
        "is_active": patient.is_active,
    }


def index_patient_document(document: Dict[str, Any]) -> None:
    """Upsert a patient document into Elasticsearch."""
    if not settings.ELASTICSEARCH_ENABLED:
        logger.info(
            "Elasticsearch is disabled; skipping patient indexing for %s",
            document["id"],
        )
        return

    client = get_es_client()
    client.index(
        index=settings.ELASTICSEARCH_PATIENT_INDEX,
        id=document["id"],
        document=document,
        refresh=True,
    )


def index_patient(patient: Patient, user: Optional[User]) -> None:
    """Create or update a patient document from ORM objects."""
    ensure_patient_index()
    index_patient_document(build_patient_document(patient, user))


def search_patients(
    query: str,
    organization_id: Optional[UUID] = None,
    size: int = 20,
) -> List[Dict[str, Any]]:
    """Search indexed patients by free-text query."""
    if not settings.ELASTICSEARCH_ENABLED:
        raise SearchUnavailableError("Elasticsearch is disabled for this environment")

    client = get_es_client()
    filters: List[Dict[str, Any]] = [{"term": {"is_active": True}}]

    if organization_id is not None:
        filters.append({"term": {"organization_id": str(organization_id)}})

    response = client.search(
        index=settings.ELASTICSEARCH_PATIENT_INDEX,
        size=size,
        query={
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "first_name^3",
                                "last_name^3",
                                "full_name^4",
                                "email",
                                "phone",
                                "mrn^5",
                            ],
                            "fuzziness": "AUTO",
                        }
                    }
                ],
                "filter": filters,
            }
        },
    )

    hits = response.get("hits", {}).get("hits", [])
    return [
        {
            "score": hit.get("_score"),
            **hit.get("_source", {}),
        }
        for hit in hits
    ]
