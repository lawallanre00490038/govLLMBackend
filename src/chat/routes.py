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
from fastapi import Form, Request, File, HTTPException
from .schemas import MessageSchemaModel, GroupedChatResponseModel, SessionSchemaModel, ChatMessageHistory, SessionListResponse, ChatSessionResponse, ChatGeneralResponse
from .schemas import DirectQueryRequest, RagQueryRequest, ChatRequestSchema, ChatResponseSchema, TopDocument, UploadResponseSchema, RagQueryResponse, FeatureListResponse
from src.users.schemas import TokenUser
from src.errors import ChatAPIError
import uuid
from typing import Optional, List


chat_router = APIRouter()
chat_client = ChatAPIClient()

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "audio/mpeg", "audio/wav"}

@chat_router.post("/", response_model=ChatResponseSchema, include_in_schema=True)
async def handle_chat(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: ChatRequestSchema,
    current_user: TokenUser = Depends(get_current_user)
):
    """
      Send a chat request to the external API and save the response in the database.
      Args:
          data (str): The data to send in the request.
      Returns:
          str: The response from the API.
    """

    user_id = str(current_user.id)
    result = await chat_client.send_chat_request(
        session=session,
        endpoint="chat", 
        data={"message": request.message, "user_id": user_id}, 
        token=current_user.access_token,
        session_id=request.session_id
    )

    return ChatResponseSchema(
        message=result.get("response", "No response"),
        session_id=result.get("session_id", None),
        session_name=result.get("session_name", None),
        history=result.get("chat_history", []),
    )



@chat_router.post("/stream")
async def handle_chat(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: ChatRequestSchema,
    current_user: TokenUser = Depends(get_current_user)
):
    """
      Send a chat request to the external API and streams the response in a custom way.
      Args:
          message (str): The message to send in the request.
          token (str): The authorization token.
      Returns:
          StreamingResponse: The response from the API.
    """

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

# =============================================================================



@chat_router.get("/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    user: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all sessions for a user.
    """
    return await chat_client.get_user_sessions(
        user=user,
        session=session
    )



@chat_router.get("/session/{session_id}", response_model=ChatSessionResponse)
async def get_chat_by_session_id(session_id: str, session: AsyncSession = Depends(get_session)):
    """
    Get chats by session ID.
    """
    return await chat_client.get_chat_by_session_id(
        session_id=session_id,
        session=session
    )


@chat_router.delete("/session/{session_id}", response_model=ChatGeneralResponse)
async def delete_session(session_id: str, session: AsyncSession = Depends(get_session)):
    """
    Delete a chat session.
    """
    return await chat_client.delete_session(
        session_id=session_id,
        session=session
    )



@chat_router.post("/clear-chat", response_model=ChatGeneralResponse)
async def clear_all_user_chats(
    user: TokenUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await chat_client.clear_all_user_chats(
        user=user,
        session=session
    )


# ====================================================================================


@chat_router.post("/upload_file_with_chat", response_model=ChatResponseSchema, include_in_schema=True)
async def file_upload_with_chat(
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    document_id: Optional[str] = Form(None),
    clear_history: bool = Form(False),
    current_user: TokenUser = Depends(get_current_user)
):
    """
    Upload a file to the chat service and save the chat interaction.
    """

    if session_id:
        external_session_id = await chat_client.replace_session_id_with_external_id(
            session_id=session_id,
            session=session
        )

    # Call external file chat upload endpoint
    response = await chat_client.proxy_chat_upload_service(
        session=session,
        endpoint="chat/upload",
        file=file,
        message=message,
        session_id=external_session_id,
        document_id=document_id,
        clear_history=clear_history,
        token=current_user.access_token
    )

    # Get or create the chat session
    chat_session = await chat_client.get_or_create_chat_session(
        session=session,
        user_id=current_user.id,
        external_session_id=response.get("session_id")
    )

    # Save the file-related message pair
    chat_session_id, history = await chat_client.save_full_chat_session(
        session=session,
        chat_session=chat_session,
        user_message=message,
        ai_response=response.get("response")
    )

    return ChatResponseSchema(
        message=response.get("response"),
        session_id=chat_session_id,
        history=history[-2:]
    )


@chat_router.post("/file/upload")
async def upload_file(
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
    current_user: TokenUser = Depends(get_current_user),
):
    """
      Upload a file to the chat service of type in any: (pdf, image/png/jpeg, and audio/wav/mpeg).
      Args:
          file (UploadFile): The file to upload.
      Returns:
          str: The response from the API.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
    
    result = await chat_client.proxy_file_upload_service(
        session=session,
        endpoint="upload",
        file=file,
        token=current_user.access_token
    )

    return UploadResponseSchema(
        message=result.get("message", "File uploaded successfully"),
        status="success",
    )


@chat_router.post("/query/rag", response_model=RagQueryResponse)
async def query_rag(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: RagQueryRequest,
    current_user: TokenUser = Depends(get_current_user)
):
    try:
        result = await chat_client.proxy_rag_query_service(
            session=session,
            endpoint="query/rag",
            payload=request.model_dump(),
            token=current_user.access_token
        )

        chat_session = await chat_client.get_or_create_chat_session(
            session=session,
            user_id=current_user.id,
            external_session_id=result.get("session_id")
        )

        chat_session_id, history = await chat_client.save_full_chat_session(
            session=session,
            chat_session=chat_session,
            user_message=request.query,
            ai_response=result.get("answer")
        )

        return RagQueryResponse(
            session_id=chat_session_id,
            answer=result.get("answer", "No answer provided"),
            top_documents=[
                TopDocument(**doc) for doc in result.get("top_documents", [])
            ],
            history=history[-2:]
        )

    except Exception as e:
        print(f"RAG query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@chat_router.post("/query/direct", response_model=ChatResponseSchema)
async def query_direct(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: DirectQueryRequest,
    current_user: TokenUser = Depends(get_current_user)
):
    try:
        result = await chat_client.proxy_direct_query_service(
            session=session,
            endpoint="query/direct",
            payload=request.model_dump(),
            user=current_user
        )

        # Get or create chat session
        chat_session = await chat_client.get_or_create_chat_session(
            session=session,
            user_id=current_user.id,
            external_session_id=result.get("session_id")
        )

        # Save conversation
        chat_session_id, history = await chat_client.save_full_chat_session(
            session=session,
            chat_session=chat_session,
            user_message=request.query,
            ai_response=result.get("answer")
        )

        return ChatResponseSchema(
            status="success",
            message=result.get("answer"),
            session_id=chat_session_id,
            history=history[-2:]
        )

    except Exception as e:
        print(f"Direct query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# get all chat for a session id
@chat_router.get("/session/{session_id}/chats", response_model=List[ChatMessageHistory])
async def get_chats(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: TokenUser = Depends(get_current_user)
):
    """
      Fetch all chat messages for a given session ID.
      Args:
          session_id (UUID): The session ID.
      Returns:
          ChatResponseSchema: The chat response schema.
    """
    result = await chat_client.get_chats_by_session(session_id=session_id, session=session)

    return result
    

@chat_router.post("/list_features", response_model=FeatureListResponse)
async def list_features(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: TokenUser = Depends(get_current_user)
):
    """
      List all features.
      Returns:
          dict: The response from the API.
    """
    result = await chat_client.list_features_service(
        session=session,
        endpoint="features",
        token=current_user.access_token
    )

    return FeatureListResponse(
        features=result.get("features", [])
    )
