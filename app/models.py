from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    # username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    # full_name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)