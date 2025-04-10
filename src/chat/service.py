import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from src.db.models import ChatSession, User, ChatMessage
import uuid
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import Optional
from fastapi import UploadFile
from typing import Dict, Any
from src.errors import ChatAPIError, DatabaseError, InvalidToken, ChatSessionSaveError, NoChatSessionsFound, FileUploadError, ChatUploadError, RAGQueryError, DirectQueryError
from sqlalchemy.exc import SQLAlchemyError
from .schemas import FolderUploadCreateModel


class ChatAPIClient:
  def __init__(self):
      self.base_url = "https://bizllminer.equalyz.ai"
      self.client = httpx.AsyncClient()

  # Send chat request to the external API
  async def send_chat_request(self, session: AsyncSession, endpoint: str, data: dict, token: str):
  
    try:
        response = await self.client.post(
            f"{self.base_url}/{endpoint}",
            json=data,
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 401:
            raise InvalidToken()
        
        response.raise_for_status()
        result = response.json()

        # Save session and messages
        session_id = await self.save_full_chat_session(
            session=session,
            user_id=data["user_id"],
            external_session_id=result.get("session_id"),
            user_message=data["message"],
            ai_response=result.get("response")
        )

        print("Chat API response:", result, session_id)

        return result["response"]

    except Exception as e:
      print(e)
      raise ChatAPIError()

    # Save full chat session and messages
  async def save_full_chat_session(
        self, 
        session: AsyncSession, 
        user_id: uuid.UUID, 
        external_session_id: Optional[str], 
        user_message: str, 
        ai_response: str
    ):
      # Save Chat Session
      try:
        chat_session = ChatSession(user_id=user_id, external_session_id=external_session_id)
        session.add(chat_session)
        await session.flush()

        # Save User Message
        user_msg = ChatMessage(session_id=chat_session.id, sender="user", content=user_message)
        session.add(user_msg)

        # Save AI Response
        ai_msg = ChatMessage(session_id=chat_session.id, sender="ai", content=ai_response)
        session.add(ai_msg)

        await session.commit()
        print(f"Saved session {chat_session.id} with 2 messages.")
        return chat_session.id
      except Exception:
        await session.rollback()
        raise ChatSessionSaveError()


  async def get_chats_by_user_grouped(
    self,
    user_id: uuid.UUID,
    session: AsyncSession,
  ) -> dict:
    """
    Retrieve all chat messages grouped by session ID for a specific user.
    """
    # Query to fetch sessions and their messages
    try:
      query = (
          select(ChatSession.id, ChatMessage)
          .join(ChatMessage, ChatSession.id == ChatMessage.session_id)
          .where(ChatSession.user_id == user_id)
          .order_by(ChatMessage.created_at.asc())
      )
    except Exception as e:
       raise DatabaseError()

    result = await session.execute(query)
    rows = result.all()

    # Group messages by session ID
    grouped_chats = {}
    for row in rows:
        session_id, message = row
        if session_id not in grouped_chats:
            grouped_chats[session_id] = []
        grouped_chats[session_id].append({
            "message_id": message.id,
            "sender": message.sender,
            "content": message.content,
            "created_at": message.created_at,
        })

    return {
        "user_id": user_id,
        "sessions": [
            {"session_id": sid, "messages": msgs}
            for sid, msgs in grouped_chats.items()
        ]
    }
  


  async def proxy_chat_upload_service(
    self,
    session: AsyncSession,
    endpoint: str,
    file: UploadFile,
    message: str,
    session_id: str,
    document_id: str,
    clear_history: bool,
    token: str,

  ):
    file_bytes = await file.read()
    files = {
        "file": (file.filename, file_bytes, file.content_type),
        "message": (None, message),
        "clear_history": (None, str(clear_history).lower()),
    }
    if session_id:
        files["session_id"] = (None, session_id)
    if document_id:
        files["document_id"] = (None, document_id)

    try:
        response = await self.client.post(
          f"{self.base_url}/{endpoint}",
          files=files,
          headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()

        print(f"Chat upload response: {response.json()}")
        return response.json()
    except Exception as e:
       raise ChatUploadError()


  async def proxy_file_upload_service(
      self,
      session: AsyncSession,
      endpoint: str,
      file: UploadFile,
      token: str,
    ):
      file_bytes = await file.read()
      files = {
          "file": (file.filename, file_bytes, file.content_type),
      }

      try:
          timeout = httpx.Timeout(10.0)
          response = await self.client.post(
            f"{self.base_url}/{endpoint}",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout
          )
          response.raise_for_status()
          return response.json()
      except httpx.HTTPStatusError as e:
        print("HTTP error:", e.response.status_code)
        print("Response content:", e.response.text)
        raise FileUploadError()


  async def proxy_rag_query_service(
        self,
        session: AsyncSession, 
        endpoint: str,
        payload: dict,
        token: str,
      ):
      try:
          response = await self.client.post(
              f"{self.base_url}/{endpoint}",
              json=payload,
              headers={"Authorization": f"Bearer {token}"}
          )
          response.raise_for_status()
          return response.json()
      except Exception as e:
          raise RAGQueryError()


  async def proxy_direct_query_service(
      self,
      session: AsyncSession, 
      endpoint: str,
      payload: dict,
      user: str,
    ):
    try:
      response = await self.client.post(
          f"{self.base_url}/{endpoint}",
          json=payload, 
          headers={"Authorization": f"Bearer {user.access_token}"}
        )
      response.raise_for_status()
      result =  response.json()

      # Save session and messages
      await self.save_full_chat_session(
          session=session,
          user_id=user.id,
          external_session_id=result.get("session_id"),
          user_message=payload["query"],
          ai_response=result.get("answer")
      )

      return result["answer"]
    except Exception as e:
        raise DirectQueryError()
    
  async def list_features_service(
    self,
    session: AsyncSession,
    endpoint: str,
    token: str,
  ):
    try:
        response = await self.client.get(
            f"{self.base_url}/{endpoint}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise ChatAPIError()
