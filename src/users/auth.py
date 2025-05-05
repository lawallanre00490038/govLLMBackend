import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from itsdangerous import URLSafeTimedSerializer

import jwt
from passlib.context import CryptContext
from src.config import settings
from src.errors import UserAlreadyExists, InvalidCredentials, AccountNotVerified, UserNotFound, NotAuthenticated
from fastapi import Request, Response, HTTPException
import secrets
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from src.config import settings
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import LoginResponseReadModel, TokenUser, UserModel
from typing import Optional
from passlib.hash import bcrypt

passwd_context = CryptContext(schemes=["bcrypt"])
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300

class OptionalOAuth2Scheme(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            return await super().__call__(request)
        except Exception:
            return None

# Replace with the optional version
optional_oauth2_scheme = OptionalOAuth2Scheme(tokenUrl="token")


def generate_passwd_hash(password: str) -> str:
    hash = passwd_context.hash(password)
    return hash

def verify_password(password: str, hash: str) -> bool:
    return passwd_context.verify(password, hash)

def get_password_hash(password: str):
    return passwd_context.hash(password)


def decode_token(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token, key=settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )

        return token_data

    except jwt.PyJWTError as e:
        logging.exception(e)
        return None

serializer = URLSafeTimedSerializer(
    secret_key=settings.JWT_SECRET, salt="email-configuration"
)

def create_url_safe_token(data: dict):
    token = serializer.dumps(data)
    return token

def decode_url_safe_token(token:str):
    try:
        token_data = serializer.loads(token)

        return token_data
    
    except Exception as e:
        logging.error(str(e))


def create_access_token(user, expires_delta: timedelta | None = None):
    try:
        if not user.is_verified:
            raise AccountNotVerified()
        to_encode = {
            
            "sub": user.email,
            "id": str(user.id),
            "is_verified": user.is_verified,
            "full_name": user.full_name if user.full_name else None,
            "exp": datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        }
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    except Exception as e:
        logging.error(f"Error creating access token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(optional_oauth2_scheme),
):
    # First, check Authorization header (OAuth2)
    access_token = token or request.cookies.get("access_token")

    if not access_token:
        raise NotAuthenticated()

    try:
        payload = jwt.decode(access_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("id")
        full_name = payload.get("full_name") if payload.get("full_name") else None

        if not email or not user_id:
            raise HTTPException(status_code=401, detail="Token missing fields")

        return TokenUser(
            full_name=full_name if full_name else None,
            email=email,
            id=user_id,
            is_verified=payload.get("is_verified"),
            access_token=access_token,
            token_type="bearer"
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def verify_email_response(user, access_token: str, response):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=18000,
        samesite="none",
        secure=True,
    )

    new_user = UserModel.model_validate(user)

    print("User email verified successfully: ", new_user)
    return LoginResponseReadModel(
        status=True,
        message="User created successfully",
        data=user
    )











# from fastapi import APIRouter, Request, HTTPException
# from fastapi.responses import RedirectResponse
# from src.config import settings
# from src.db.main import get_session
# from src.users.schemas import GetTokenRequest, GooglePayload
# import uuid
# from google.oauth2 import id_token
# from google.auth.transport import requests
# import httpx


# async def google_login(code: str, request: Request):
#     """
#         This routes is automatically called by the google route
#         Handle the Google sign/signup callback.
#         Responsible for exchanging the code for an access token and validating the token.
#         Send the user data to the user.
#     """
#     token_request_uri = "https://oauth2.googleapis.com/token"
#     data = {
#         'code': code,
#         'client_id': settings.GOOGLE_CLIENT_ID,
#         'client_secret': settings.GOOGLE_CLIENT_SECRET,
#         'redirect_uri': "postmessage",
#         'grant_type': 'authorization_code',
#     }


#     headers = {"Content-Type": "application/x-www-form-urlencoded"}
#     async with httpx.AsyncClient() as client:
#         response = await client.post(token_request_uri, data=data, headers=headers)
#         response.raise_for_status()
#         token_response = response.json()

#     id_token_value = token_response.get('id_token')
#     if not id_token_value:
#         raise HTTPException(status_code=400, detail="Missing id_token in response.")

#     try:
#         id_info = id_token.verify_oauth2_token(
#             id_token_value, requests.Request(), 
#             settings.GOOGLE_CLIENT_ID,
#             clock_skew_in_seconds=2
#         )

#         payload: GooglePayload = {
#             "sub": id_info.get('sub'),
#             "email": id_info.get('email'),
#             "name": id_info.get('name'),
#             "picture": id_info.get('picture'),
#             "is_verified": id_info.get('email_verified'),
#             "verification_token": str(uuid.uuid4())
#         }

#         # request.session["user_data"] = payload 
#         # request.state.session = await get_session().__anext__() 
#         # print("The payload is", payload)
#         # response = await validate(request)
#         return payload

#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=f"Invalid id_token: {str(e)}")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail="Internal Server Error")
