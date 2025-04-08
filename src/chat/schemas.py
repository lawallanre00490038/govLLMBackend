from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID
from pydantic import BaseModel


class CreateChat(BaseModel):
    message: str

class GetAllChatRequestSchema(BaseModel):
    user_id: UUID
    page: int
    size: int
    sort_by: Optional[str] = "created_at"
    order: Optional[str] = "desc"

    class Config:
        from_attributes = True


class MessageSchemaModel(BaseModel):
    message_id: UUID
    sender: str
    content: str
    created_at: datetime

class SessionSchemaModel(BaseModel):
    session_id: UUID
    messages: List[MessageSchemaModel]

class GroupedChatResponseModel(BaseModel):
    user_id: UUID
    sessions: List[SessionSchemaModel]





class ChatRequestSchema(BaseModel):
    message: str

class Message(BaseModel):
    content: str
    sender: str
    created_at: datetime

class ChatSession(BaseModel):
    session_id: UUID
    messages: List[Message]

class GroupedChatResponse(BaseModel):
    user_id: UUID
    sessions: List[ChatSession]

class FileUploadResponse(BaseModel):
    document_id: str
    file_name: str
    file_size: int

class RagQueryRequest(BaseModel):
    query: str
    top_k: int = 10
    rerank_k: int = 3
    feature: Optional[str] = None

class DirectQueryRequest(BaseModel):
    query: str