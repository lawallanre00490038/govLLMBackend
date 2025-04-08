from typing import Any, Callable
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI, status
from sqlalchemy.exc import SQLAlchemyError

class GovLLMiner(Exception):
     """Base class for all Bookly-related exceptions."""
     def __init__(self, message: str = "An error occurred", error_code: str = "error"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class InvalidToken(GovLLMiner):
    """User has provided an invalid or expired token"""

    pass


class RevokedToken(GovLLMiner):
    """User has provided a token that has been revoked"""

    pass


class AccessTokenRequired(GovLLMiner):
    """User has provided a refresh token when an access token is needed"""

    pass


class RefreshTokenRequired(GovLLMiner):
    """User has provided an access token when a refresh token is needed"""

    pass



class UserAlreadyExists(GovLLMiner):
    """User has provided an email for a user who exists during sign up."""

    def __init__(self, message: str = "User with email already exists"):
        super().__init__(message=message, error_code="user_exists")


# ========================================== Chat API & Session Errors
class ChatAPIError(GovLLMiner):
    """Raised when an error occurs while communicating with the external chat API."""
    def __init__(self, message: str = "Error communicating with chat API"):
        super().__init__(message=message, error_code="chat_api_error")


class ChatSessionSaveError(GovLLMiner):
    """Raised when saving a chat session or messages fails."""
    def __init__(self, message: str = "Failed to save chat session or messages"):
        super().__init__(message=message, error_code="chat_session_save_error")


class NoChatSessionsFound(GovLLMiner):
    """Raised when no chat sessions are found for the user."""
    def __init__(self, message: str = "No chat sessions found"):
        super().__init__(message=message, error_code="no_chats_found")



# ======================================== File Upload Errors
class FileUploadError(GovLLMiner):
    """Raised when a file upload fails."""
    def __init__(self, message: str = "File upload failed"):
        super().__init__(message=message, error_code="file_upload_error")


class ChatUploadError(GovLLMiner):
    """Raised when a chat-related file upload fails."""
    def __init__(self, message: str = "Chat upload failed"):
        super().__init__(message=message, error_code="chat_upload_error")



# ============================================  RAG and Direct Query Errors
class RAGQueryError(GovLLMiner):
    """Raised when a RAG (retrieval-augmented generation) query fails."""
    def __init__(self, message: str = "RAG query failed"):
        super().__init__(message=message, error_code="rag_query_error")


class DirectQueryError(GovLLMiner):
    """Raised when a direct query to the model fails."""
    def __init__(self, message: str = "Direct query failed"):
        super().__init__(message=message, error_code="direct_query_error")


class DatabaseError(GovLLMiner):
    """Raised when a database error occurs."""
    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message=message, error_code="database_error")


class InvalidCredentials(GovLLMiner):
    """User has provided wrong email or password during log in."""

    pass


class InsufficientPermission(GovLLMiner):
    """User does not have the neccessary permissions to perform an action."""

    pass


class UserNotFound(GovLLMiner):
    """User Not found"""

    pass


class AccountNotVerified(Exception):
    """Account not yet verified"""
    pass

def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], JSONResponse]:

    async def exception_handler(request: Request, exc: GovLLMiner):

        return JSONResponse(content=initial_detail, status_code=status_code)

    return exception_handler


def register_all_errors(app: FastAPI):
    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "User with email already exists",
                "error_code": "user_exists",
            },
        ),
    )

    app.add_exception_handler(
        UserNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "User not found",
                "error_code": "user_not_found",
            },
        ),
    )

    app.add_exception_handler(
        InvalidCredentials,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Invalid Email Or Password",
                "error_code": "invalid_email_or_password",
            },
        ),
    )
    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Token is invalid Or expired",
                "resolution": "Please get new token",
                "error_code": "invalid_token",
            },
        ),
    )

    app.add_exception_handler(
        DatabaseError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "message": "Database error occurred",
                "error_code": "database_error",
            },
        ),
    )
    app.add_exception_handler(
        RevokedToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Token is invalid or has been revoked",
                "resolution": "Please get new token",
                "error_code": "token_revoked",
            },
        ),
    )
    app.add_exception_handler(
        AccessTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Please provide a valid access token",
                "resolution": "Please get an access token",
                "error_code": "access_token_required",
            },
        ),
    )
    app.add_exception_handler(
        RefreshTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Please provide a valid refresh token",
                "resolution": "Please get an refresh token",
                "error_code": "refresh_token_required",
            },
        ),
    )
    app.add_exception_handler(
        InsufficientPermission,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "You do not have enough permissions to perform this action",
                "error_code": "insufficient_permissions",
            },
        ),
    )

    app.add_exception_handler(
        AccountNotVerified,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Account Not verified",
                "error_code": "account_not_verified",
                "resolution":"Please check your email for verification details"
            },
        ),
    )

    app.add_exception_handler(
        ChatAPIError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "message": "Error communicating with chat API",
                "error_code": "chat_api_error",
            },
        ),  
        )
    
    app.add_exception_handler(
        ChatSessionSaveError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "message": "Failed to save chat session or messages",
                "error_code": "chat_session_save_error",
            },
        ),
        )

    app.add_exception_handler(
        NoChatSessionsFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "No chat sessions found",
                "error_code": "no_chats_found",
            },
        ),
    )


    app.add_exception_handler(
        FileUploadError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "message": "File upload failed",
                "error_code": "file_upload_error",
            },
        ),
    )

    app.add_exception_handler(
        ChatUploadError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "message": "Chat upload failed",
                "error_code": "chat_upload_error",
            },
        ),
    )

    app.add_exception_handler(
        RAGQueryError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "message": "RAG query failed",
                "error_code": "rag_query_error",
            },
        ),
    )

    app.add_exception_handler(
        DirectQueryError,
        create_exception_handler(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            initial_detail={
                "message": "Direct query failed",
                "error_code": "direct_query_error",
            },
        ),
    )
    

    @app.exception_handler(500)
    async def internal_server_error(request, exc):

        return JSONResponse(
            content={
                "message": "Oops! Something went wrong",
                "error_code": "server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


    @app.exception_handler(SQLAlchemyError)
    async def database__error(request, exc):
        print(str(exc))
        return JSONResponse(
            content={
                "message": "Oops! Something went wrong",
                "error_code": "server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
