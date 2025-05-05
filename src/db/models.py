from sqlmodel import Field, SQLModel, Column, Relationship
from typing import List, Optional
from datetime import datetime
from sqlalchemy import DateTime
import sqlalchemy.dialects.postgresql  as pg
import uuid
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy import Enum
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import ForeignKey

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id : uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(back_populates="chat_sessions")
    session_name: str = Field(nullable=True, default=None)

    external_session_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    messages: List["ChatMessage"] = Relationship(back_populates="session", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id : uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4,
            
        )
    )
    session_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    session: ChatSession = Relationship(back_populates="messages")

    sender: str = Field(nullable=False)  # "user" or "ai"
    content: str = Field(nullable=False)

    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))




class User(SQLModel, table=True):
    __tablename__ = "users"
    id : uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    email: str = Field(unique=True, nullable=False)
    password: str 
    full_name: Optional[str] = Field(default=None)
    is_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None)
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime =  Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now, onupdate=datetime.utcnow))

    chat_sessions: List[ChatSession] = Relationship(back_populates="user") 

    def __repl__(self):
        return f"User {self.email}"




# ============================================Folder Models
class UploadSource(PyEnum):
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    LOCAL = "local"
    

class FolderUpload(SQLModel, table=True):
    __tablename__ = "folder_uploads"
    id : uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )

    source: UploadSource = Field(sa_column=Column(ENUM(UploadSource, name="upload_source_enum"), nullable=False)) 
    local_path: str = Field(default=None)
    file_type : str = Field(default=None)
    ingestion_status:  str = Field(default="pending")
    cleanup_status: str = Field(default="pending")
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
