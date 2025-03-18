from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from .database import Base
from .config import BREVO_API_KEY, FRONTEND_URL

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False, default="")
    disabled = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    
    # Use timezone-aware datetime
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
