import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from src.db.models import ChatSession, User, ChatMessage
import uuid
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import Optional, Dict, Any, List
from fastapi import UploadFile

from src.errors import ChatAPIError, DatabaseError, InvalidToken, ChatSessionSaveError, NoChatSessionsFound, FileUploadError, ChatUploadError, RAGQueryError, DirectQueryError
from sqlalchemy.exc import SQLAlchemyError
from .schemas import FolderUploadCreateModel


class ChatAPIClient:
  def __init__(self):
      self.base_url = "https://bizllminer.equalyz.ai"
      self.client = httpx.AsyncClient()

  async def send_chat_request(
        self,
        session: AsyncSession,
        endpoint: str,
        data: dict,
        token: str,
        session_id: Optional[uuid.UUID] = None
    ):
        try:
            # Call external API
            response = await self.client.post(
                f"{self.base_url}/{endpoint}",
                json=data,
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 401:
                raise InvalidToken()
            response.raise_for_status()
            result = response.json()

            # Reuse or create chat session
            chat_session = None

            if session_id:
                session_result = await session.execute(
                    select(ChatSession).where(ChatSession.id == session_id)
                )
                chat_session = session_result.scalar_one_or_none()
                if not chat_session:
                    raise NoChatSessionsFound()
            else:
                # New session
                chat_session = ChatSession(
                    user_id=data["user_id"],
                    external_session_id=result.get("session_id")
                )
                session.add(chat_session)
                await session.flush()

            # Save user + AI messages and return history
            saved_session_id, chat_history = await self.save_full_chat_session(
                session=session,
                chat_session=chat_session,
                user_message=data["message"],
                ai_response=result.get("response")
            )

            print("Chat API response:", result)
            return {
                "response": result["response"],
                "session_id": saved_session_id,
                "chat_history": chat_history[-2:]
            }

        except Exception as e:
            print(f"[ChatAPI] Error during chat request: {e}")
            raise ChatAPIError()
        

  async def save_full_chat_session(
        self, 
        session: AsyncSession, 
        chat_session: ChatSession, 
        user_message: str, 
        ai_response: str
    ):
    try:
        # Save user message
        user_msg = ChatMessage(
            session_id=chat_session.id,
            sender="user",
            content=user_message
        )
        session.add(user_msg)

        # Save AI response
        ai_msg = ChatMessage(
            session_id=chat_session.id,
            sender="ai",
            content=ai_response
        )
        session.add(ai_msg)

        await session.commit()
        print(f"Saved session {chat_session.id} with user & AI messages.")

        # Return updated history
        chat_history = await self._get_chat_history(chat_session.id, session)
        return chat_session.id, chat_history

    except Exception as e:
        await session.rollback()
        print(f"[ChatAPI] Error saving messages: {e}")
        raise ChatSessionSaveError()


  async def _get_chat_history(self, session_id: uuid.UUID, session: AsyncSession) -> List[Dict[str, Any]]:
      """Retrieve chat history for a given session."""
      query = (
          select(ChatMessage)
          .where(ChatMessage.session_id == session_id)
          .order_by(ChatMessage.created_at.asc())
      )
      result = await session.execute(query)
      messages = result.scalars().all()
      
      history = []
      for message in messages:
          history.append({
              "message_id": str(message.id),
              "sender": message.sender,
              "content": message.content,
              "created_at": message.created_at
          })
      return history


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
        "session_id": (None, session_id or ""),
        "document_id": (None, document_id or ""),
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }

    try:
        response = await self.client.post(
            f"{self.base_url}/{endpoint}",
            files=files,
            headers=headers
        )
        response.raise_for_status()
        print(f"Chat upload response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Upload error: {e}")
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
          print(f"Error in RAG query service: {e}")
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

      return result
    except Exception as e:
        print(f"Error in Direct query service: {e}")
        raise DirectQueryError()
    

  async def get_or_create_chat_session(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        external_session_id: Optional[str] = None
    ) -> ChatSession:
        """
            Retrieves a chat session by external_session_id or creates a new one.
        """
        if external_session_id:
            result = await session.execute(
                select(ChatSession).where(ChatSession.external_session_id == external_session_id)
            )
            chat_session = result.scalar_one_or_none()
            if chat_session:
                return chat_session
            # else:
            #     raise NoChatSessionsFound()

        # Create new session
        chat_session = ChatSession(
            user_id=user_id,
            external_session_id=external_session_id
        )
        session.add(chat_session)
        await session.flush()
        return chat_session

    
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


    
  async def get_chats_by_session(
        self,
        session_id: uuid.UUID,
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all chat messages for a specific session ID.
        """
        try:
            query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())  # oldest to newest
            )
            result = await session.execute(query)
            messages = result.scalars().all()

            return [
                {
                    "message_id": str(message.id),
                    "sender": message.sender,
                    "content": message.content,
                    "created_at": message.created_at
                }
                for message in messages
            ]

        except SQLAlchemyError as e:
            raise DatabaseError()
