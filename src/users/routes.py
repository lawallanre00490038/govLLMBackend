from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from src.db.main import get_session
from src.db.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from src.errors import UserAlreadyExists, InvalidCredentials, InvalidToken
from .schemas import LoginResponseReadModel, GetTokenRequest, RegisterResponseReadModel, UserModel, DeleteResponseModel, UserCreateModel, UserLoginModel, TokenUser, VerificationMailSchemaResponse
from .service import UserService
from typing import Annotated
from .auth import create_access_token, get_current_user
from fastapi.encoders import jsonable_encoder
from fastapi import Response, Depends
import uuid
from .auth import verify_email_response
from .schemas import GooglePayload
from src.config import settings
from datetime import timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
import httpx
import jwt
from typing import Optional
from starlette.requests import Request

auth_router = APIRouter()


@auth_router.post("/signup", response_model=RegisterResponseReadModel)
async def register_user(
    user: UserCreateModel,
    session: Annotated[AsyncSession, Depends(get_session)]
):
    """Register a new user."""
    user_service = UserService()
    try:
        new_user = await user_service.create_user(user, session)
        return RegisterResponseReadModel(
            status=True,
            message="User created successfully. Please check your mail to verify your account.",
            verification_token=new_user.verification_token,
            data=jsonable_encoder(new_user)
        )
    except UserAlreadyExists:
        raise UserAlreadyExists()


@auth_router.post("/signin", response_model=LoginResponseReadModel)
async def login(
    form_data: UserLoginModel,
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response 
):
    """Login user and return access token."""
    user_service = UserService()
    try:
        user = await user_service.authenticate_user(form_data.email, form_data.password, session)
        access_token = create_access_token(user=user)

         # Set the access token as a cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=18000,
            samesite="none",
            secure=True,
        )

        return LoginResponseReadModel(
            status=True,
            message="Login successful",
            data=user
        )
    except Exception as e:
        print("The error from the login function is", e)
        raise InvalidCredentials()




@auth_router.post("/verify-email/", response_model=LoginResponseReadModel)
async def verify_email(
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    token: str = Query(..., description="Verification token from email"),
):
    """Verify user's email using the provided token."""
    
    # Initialize UserService instance
    user_service = UserService()
    
    try:
        # Retrieve user based on the verification token
        user = await user_service.verify_token(token, session)
        print("The user from the verify email function is", user)
        
        if not user:
            raise InvalidToken()
        
        # Update user verification status
        user.is_verified = True
        user.verification_token = None
        
        # Commit changes to the database
        await session.commit()
        await session.refresh(user)
        
        # Generate access token for the verified user
        access_token = create_access_token(user=user)
        
        # Prepare response
        response = verify_email_response(user, access_token, response)
        
        return response
    
    except Exception as e:
        print("The error is", e)
        # Handle generic exceptions with a meaningful error message
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to verify email. Please try again."
        )



@auth_router.get("/users/me", response_model=TokenUser)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get details of the current user."""
    return current_user


@auth_router.post("/token", include_in_schema=True)
async def token(
    form_data: GetTokenRequest,
    response: Response,
    request: Request,
):
    """
        This routes is automatically called by the google route
        Handle the Google sign/signup callback.
        Responsible for exchanging the code for an access token and validating the token.
        Send the user data to the user.
    """
    print("The code is", form_data.code)
    tok = form_data.code

    decoded_token = jwt.decode(tok, options={"verify_signature": False})
    print("The decoded token is", decoded_token)

    request.session["user_data"] = decoded_token 
    request.state.session = await get_session().__anext__() 

    response = await validate(request, response)

    return response



# refresh token
@auth_router.get("/refresh-token", response_model=TokenUser)
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Refresh the access token for the current user."""
    access_token_expires = timedelta(minutes=300)
    access_token = create_access_token(
        user=current_user, expires_delta=access_token_expires
    )
    return TokenUser(
        email=current_user.email,
        id=current_user.id,
        is_verified=current_user.is_verified,
        access_token=access_token,
        token_type="bearer"
    )

# resend verification token
@auth_router.post("/resend-verification-token", response_model=VerificationMailSchemaResponse)
async def resend_verification_token(
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    email: str = Query(..., description="Email of the user to resend verification token"),
):
    """Resend the verification token to the user's email."""
    user_service = UserService()
    response = await user_service.resend_verification_email(email, session)

    return response
        

# delete user
@auth_router.delete("/delete-user", response_model=DeleteResponseModel)
async def delete_user(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_service = UserService()
    await user_service.delete_user(current_user, session)

    return DeleteResponseModel(
        status=True,
        message="User deleted successfully"
    )



async def validate(request: Request, response: Optional[Response] = None):
    user_data = request.session.get('user_data')
    print("The user data is from the google payload", user_data)
    user_service = UserService()
    session: AsyncSession = request.state.session

    email = user_data["email"]
    print("The email is", email)
    
    try:
        user = await user_service.get_user_by_email(email, session)
        print("The user from the validate function", user)
        if user:
            print("Following the path of existing user")
        else:
            print("Following the path of new user")

            user_model = UserCreateModel(
                email=user_data["email"],
                password="password"
            )
            user = await user_service.create_user(user_model, session, is_google=True) 

        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")
        
        access_token_expires = timedelta(minutes=300)
        print("The user going into the access token is ", user)
        access_token = create_access_token(
            user=user, expires_delta=access_token_expires
        )

        result = verify_email_response(user, access_token, response)
        
        return result

    except Exception as e:
        print("The error is", e)
        raise HTTPException(status_code=500, detail=f"Internal Server Error, {e}")
