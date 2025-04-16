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
from .schemas import MessageSchemaModel, GroupedChatResponseModel, SessionSchemaModel
from .schemas import DirectQueryRequest, RagQueryRequest, ChatRequestSchema, ChatResponseSchema, TopDocument, UploadResponseSchema, RagQueryResponse, FeatureListResponse
from src.users.schemas import TokenUser
from src.errors import ChatAPIError
import uuid
from typing import Optional


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
        token=current_user.access_token
    )
    return ChatResponseSchema(
        message=result.get("message", "No response"),
        session_id=result.get("session_id", None),
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
      Upload a file to the chat service.
      Args:
          file (UploadFile): The file to upload.
          message (str): The message to send with the file.
          session_id (str, optional): The session ID. Defaults to None.
          document_id (str, optional): The document ID. Defaults to None.
          clear_history (bool, optional): Whether to clear history. Defaults to False.
      Returns:
          str: The response from the API.
    """
    response = await chat_client.proxy_chat_upload_service(
      session=session,
      endpoint="chat/upload",
      file=file, 
      message=message, 
      session_id=session_id, 
      document_id=document_id, 
      clear_history=clear_history,
      token=current_user.access_token
    )

    # chat_session_id = await chat_client.save_full_chat_session(
    #     session=session,
    #     user_id=current_user.id,
    #     external_session_id=response.get("session_id"), 
    #     user_message=message,
    #     ai_response=response.get("response")
    # )

    # print(f"Chat session ID: {chat_session_id}")

    return ChatResponseSchema(
        message=response.get("response"),
        # session_id=chat_session_id,
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
    try:
        result = await chat_client.proxy_rag_query_service(
            session=session,
            endpoint="query/rag",
            payload=request.model_dump(),
            token=current_user.access_token
        )

        # THIS
        chat_session_id = await chat_client.save_full_chat_session(
            session=session,
            user_id=current_user.id,
            external_session_id=result.get("session_id", None),
            user_message=request.query,
            ai_response=result.get("answer")
        )
        
        print(f"Chat session ID: {chat_session_id}")
        return RagQueryResponse(
            session_id=chat_session_id,
            answer=result.get("answer", "No answer provided"),
            top_documents=[
                TopDocument(**doc) for doc in result.get("top_documents", [])
            ]
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
    """
      Direct query endpoint
      Args:
          {
            "query": "What is the capital of France?"
          }
      Returns:
          str: The response from the API.
    """
    try:
        result = await chat_client.proxy_direct_query_service(
            session=session,
            endpoint="query/direct",
            payload=request.model_dump(),
            user=current_user
        )


        # THIS
        chat_session_id = await chat_client.save_full_chat_session(
            session=session,
            user_id=current_user.id,
            external_session_id=result.get("session_id", None),
            user_message=request.query,
            ai_response=result
        )

        print(f"Chat session ID: {chat_session_id}")
        
        return ChatResponseSchema(
            status="success",
            message=result,
            session_id=chat_session_id
        )
    except Exception as e:
        print(f"Direct query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

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
