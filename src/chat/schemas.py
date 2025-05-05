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


class FolderUploadCreateModel(BaseModel):
    file_path: str
    file_type: str


class ChatRequestSchema(BaseModel):
    message: str
    session_id: Optional[UUID] = None



class ChatMessageHistory(BaseModel):
    message_id: UUID
    sender: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatTurn(BaseModel):
    message_id: UUID
    sender: str
    content: str
    created_at: datetime
class ChatResponseSchema(BaseModel):
    status: Optional[str] = "success"
    message: str
    session_id: Optional[UUID] = None
    session_name: Optional[str] = None
    history: Optional[List[ChatTurn]] = None


class UploadResponseSchema(BaseModel):
    status: Optional[str] = "success"
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






class TopDocument(BaseModel):
    id: int
    source: str
    score: float
    text: str


class RagQueryResponse(BaseModel):
    session_id: Optional[UUID] = None
    answer: str
    top_documents: List[TopDocument]
    history: Optional[List[ChatTurn]] = None


class FeatureListResponse(BaseModel):
    features: List[str]




# Session schemas


class SessionResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    session_name: Optional[str] = None
    created_at: datetime

# For a list response
class SessionListResponse(BaseModel):
    status: Optional[bool] = True
    session: List[SessionResponse]


class ChatTurn(BaseModel):
    user: str
    ai: Optional[str] = None

class ChatSessionResponse(BaseModel):
    status: Optional[bool] = True
    session_id: UUID
    session_name: Optional[str] = None
    chat_history: List[ChatTurn]

class ChatGeneralResponse(BaseModel):
    status: Optional[bool] = True
    message: str

class SessionIdGeneralRequest(BaseModel):
    session_id: UUID
