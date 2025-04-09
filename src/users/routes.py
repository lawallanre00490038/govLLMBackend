from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from src.db.main import get_session
from src.db.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from src.errors import UserAlreadyExists, InvalidCredentials, InvalidToken
from .schemas import LoginResponseReadModel, RegisterResponseReadModel, UserModel, DeleteResponseModel, UserCreateModel, UserLoginModel, TokenUser, VerificationMailSchemaResponse
from .service import UserService
from .auth import create_access_token, get_current_user
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


@auth_router.post("/login", response_model=LoginResponseReadModel)
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
            max_age=3600,
            samesite="lax"
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



@auth_router.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get details of the current user."""
    return current_user


@auth_router.get("/signin/google/")
async def google_login(request: Request):
    """
        Redirect the user to Google login page.
        if authenticated, return success else raise a 400 error.
    """
    print("The request is", request.headers.get("Referer"))
    redirect_uri = request.url_for('auth')
    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?GOOGLE_CLIENT_ID={settings.CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=openid email profile"

    return RedirectResponse(url=google_auth_url)

@auth_router.get("/auth", include_in_schema=False)
async def auth(code: str, request: Request):
    """
        This routes is automatically called by the google route
        Handle the Google sign/signup callback.
        Responsible for exchanging the code for an access token and validating the token.
        Send the user data to the user.
    """
    token_request_uri = "https://oauth2.googleapis.com/token"
    data = {
        'code': code,
        'GOOGLE_CLIENT_ID': settings.CLIENT_ID,
        'GOOGLE_CLIENT_SECRET': settings.CLIENT_SECRET,
        'redirect_uri': request.url_for('auth'),
        'grant_type': 'authorization_code',
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_request_uri, data=data)
        response.raise_for_status()
        token_response = response.json()

    id_token_value = token_response.get('id_token')
    if not id_token_value:
        raise HTTPException(status_code=400, detail="Missing id_token in response.")

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_value, requests.Request(), 
            settings.CLIENT_ID,
            clock_skew_in_seconds=2
        )

        payload: GooglePayload = {
            "sub": id_info.get('sub'),
            "email": id_info.get('email'),
            "name": id_info.get('name'),
            "picture": id_info.get('picture'),
            "is_verified": id_info.get('email_verified'),
            "verification_token": str(uuid.uuid4())
        }

        request.session["user_data"] = payload 
        print("The payload is", payload)
        response = await validate(request)
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid id_token: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")




# refresh token
@auth_router.get("/refresh-token", response_model=TokenUser)
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Refresh the access token for the current user."""
    access_token_expires = timedelta(minutes=30)
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


async def validate(request: Request):
    user_data = request.session.get('user_data')
    print("The user data is", user_data)
    user_service = UserService()
    user = user_service.get_user_by_email(user_data["email"], request.session)
    try:
        user = await user_service.get_user_by_email(user_data["email"], request.session)
        print("The user from the validate function", user)
        if user:
            print("Following the path of existing user")
        else:
            print("Following the path of new user")
            user = await user_service.create_user(user_data, request.session) 

        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")
        
        access_token_expires = timedelta(minutes=30)
        print("The user going into the access token is ", user)
        access_token = create_access_token(
            user=user, expires_delta=access_token_expires
        )

        frontend_redirect_url = f"http://localhost:3000/profile"
        
        return RedirectResponse(
            url=frontend_redirect_url,
            headers={
                "Set-Cookie": f"access_token={access_token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=1800",
            },
            status_code=302,
        )

    except Exception as e:
        print("The error is", e)
        raise HTTPException(status_code=500, detail=f"Internal Server Error, {e}")
