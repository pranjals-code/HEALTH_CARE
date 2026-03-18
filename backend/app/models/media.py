"""
Media upload model for simple file storage metadata.
"""

from sqlalchemy import Column, DateTime, Integer, String
from datetime import datetime

from app.models.base import Base


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
