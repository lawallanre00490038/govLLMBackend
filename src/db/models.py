from sqlmodel import Field, SQLModel, Column, Relationship
from typing import List, Optional
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy.dialects.postgresql  as pg
import uuid
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.orm import relationship

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

    external_session_id: Optional[str] = Field(default=None)  # Save the API session_id
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    messages: List["ChatMessage"] = Relationship(back_populates="session")  # Add message relationship


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id : uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    session_id: uuid.UUID = Field(foreign_key="chat_sessions.id")
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
