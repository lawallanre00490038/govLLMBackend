# routes/chat.py
from fastapi import APIRouter, Depends, UploadFile
from src.users.auth import get_current_user
from .service import ChatAPIClient
from src.db.models import User
from fastapi.responses import StreamingResponse
import asyncio
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.main import get_session
from uuid import UUID
from src.db.models import ChatMessage, User
from fastapi import Form, Request, File
from .schemas import MessageSchemaModel, GroupedChatResponseModel, SessionSchemaModel
from .schemas import DirectQueryRequest, RagQueryRequest, ChatRequestSchema
from src.errors import ChatAPIError
import uuid
from typing import Optional


chat_router = APIRouter()
chat_client = ChatAPIClient()

@chat_router.post("/")
async def handle_chat(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: ChatRequestSchema,
    current_user: User = Depends(get_current_user)
):
    """
      Send a chat request to the external API and save the response in the database.
      Args:
          data (str): The data to send in the request.
          token (str): The authorization token.
      Returns:
          str: The response from the API.
    """

    user_id = str(current_user.id)
    result = await chat_client.send_chat_request(
        session=session,
        endpoint="chat", 
        data={"message": request.message, "user_id": user_id}, 
        token=current_user.access_token
    )
    return result




@chat_router.post("/stream")
async def handle_chat(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: ChatRequestSchema,
    current_user: User = Depends(get_current_user)
):
    """
      Send a chat request to the external API and streams the response in a custom way.
      Args:
          message (str): The message to send in the request.
          token (str): The authorization token.
      Returns:
          StreamingResponse: The response from the API.
    """
    # user_id = str(current_user.id)

    # result = await chat_client.send_chat_request(
    #     session=session,
    #     endpoint="chat", 
    #     data={"message": request.message, "user_id": user_id}, 
    #     token=current_user.access_token
    #   )
    
    # full_response = result

    # async def simulated_event_generator(content: str):
    #   print(content)
    #   for word in content.split():
    #       await asyncio.sleep(0.1) 
    #       yield f"data: {word} \n"

    # return StreamingResponse(
    #     simulated_event_generator(full_response),
    #     media_type="text/event-stream"
    # )

    try:
      response = await chat_client.send_chat_request(
          session=session,
          endpoint="chat",
          data={
              "message": request.message,
              "user_id": str(current_user.id)
          },
          token=current_user.access_token
      )

      async def event_stream():
          for word in response.split():
              yield f"data: {word}\n\n"
              await asyncio.sleep(0.05)

      return StreamingResponse(
          event_stream(),
          media_type="text/event-stream",
          headers={"X-Stream-ID": str(uuid.uuid4())}
      )
    except Exception as e:
      raise ChatAPIError()



@chat_router.get("/{user_id}/chats", response_model=GroupedChatResponseModel)
async def get_grouped_chats(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    
    """ 
      Fetch all chat sessions for a user and group them by session_id.
      Args:
          user_id (UUID): The user ID.
          session (AsyncSession): The database session.
      Returns:
          GroupedChatResponse: The grouped chat response.
    """
    result = await chat_client.get_chats_by_user_grouped(user_id=user_id, session=session)
    
    return GroupedChatResponseModel(
        user_id=result["user_id"],
        sessions=[
            SessionSchemaModel(session_id=s["session_id"], messages=[
                MessageSchemaModel(**msg) for msg in s["messages"]
            ])
            for s in result["sessions"]
        ]
    )


chat_router.post("/upload")
async def chat_upload(
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    document_id: Optional[str] = Form(None),
    clear_history: bool = Form(False),
    current_user: User = Depends(get_current_user)
    
):
    """
      Upload a file to the chat service.
      Args:
          session (AsyncSession): The database session.
          file (UploadFile): The file to upload.
          message (str): The message to send with the file.
          session_id (str, optional): The session ID. Defaults to None.
          document_id (str, optional): The document ID. Defaults to None.
          clear_history (bool, optional): Whether to clear history. Defaults to False.
          current_user (User): The current user.
      Returns:
          str: The response from the API.
    """
    return await chat_client.proxy_chat_upload_service(
      session,
      "/chat/upload",
      file, 
      message, 
      session_id, 
      document_id, 
      clear_history,
      current_user.access_token
    )


@chat_router.post("/file/upload")
async def upload_file(
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
  ):
    """
      General file upload endpoint
      Args:
          file (UploadFile): The file to upload.
          token (str): The authorization token.
      Returns:
          str: The response from the API.
    """
    return await chat_client.proxy_file_upload_service(
      session=session,
      endpoint="upload",
      file=file,
      token=current_user.access_token
    )


@chat_router.post("/query/rag")
async def query_rag(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: RagQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
      RAG query endpoint, sends a query to the RAG service and returns the results.
      Args:
          {
            "query": "What is the capital of France?",
            "top_k": 10,
            "rerank_k": 3,
            "feature": "some_feature"
          }

      Returns:
          str: The response from the API.
    """
    return await chat_client.proxy_rag_query_service(
        session=session,
        endpoint="query/rag",
        payload=request.model_dump(),
        token=current_user.access_token
    )


@chat_router.post("/query/direct")
async def query_direct(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: DirectQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
      Direct query endpoint
      Args:
          {
            "query": "What is the capital of France?"
          }
      Returns:
          str: The response from the API.
    """
    return await chat_client.proxy_direct_query_service(
        session=session,
        endpoint="query/direct",
        payload=request.model_dump(),
        user=current_user
      )