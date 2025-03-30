from sqlmodel import Field, SQLModel, Column, Relationship
from typing import List, Optional
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy.dialects.postgresql  as pg
import uuid


class User(SQLModel, table=True):
    __tablename__ = "users"
    uid : uuid.uuid4 = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )

    email: str = Field(unique=True, nullable=False)
    password: str 
    is_verified: bool = Field(default=False)
    is_first_login: bool = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = Field(default="user")
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime =  Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now, onupdate=datetime.utcnow))

    def __repl__(self):
        return f"User {self.email}"
