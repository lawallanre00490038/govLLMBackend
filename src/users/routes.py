from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
import httpx
import uuid
from sqlalchemy.orm import Session
from fastapi import Response
from datetime import timedelta
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from src.configs.config import CLIENT_ID, CLIENT_SECRET
from google.oauth2 import id_token
from google.auth.transport import requests
from src.db.database import engine, Base, get_db, SessionLocal
from fastapi.responses import HTMLResponse
from src.models.user import User
from .schemas import  UserInDB, LoginResponseModel, GetTokenResponse, RegisterResponseModel, LoginRequestModel, GooglePayload, GetTokenRequest
from .utils.auth import not_verified_user, authenticate_user, create_access_token, get_current_active_user, get_password_hash, authenticate_google_user, add_google_user
from .utils.email import send_verification_email
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

Base.metadata.create_all(bind=engine)
load_dotenv()

router = APIRouter()
oauth = OAuth()
import os

# Detect if running in development mode
IS_DEV = os.getenv("ENV", "development") == "development"
print("Running in development mode:", IS_DEV)



@router.post("/signup/", response_model=RegisterResponseModel)
async def register_user(
    user: UserInDB,
    db: Session = Depends(get_db),
):
    """
    Register a new user and send a verification email in the background.
    """
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    verification_token = str(uuid.uuid4()) 

    db_user = User(
        email=user.email,
        password=get_password_hash(user.password),
        is_email_verified=False,
        verification_token=verification_token
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    print(f"Generated Token for {db_user.email}: {verification_token}")
    print(f"Stored Token in DB: {db_user.verification_token}")
    send_verification_email(user.email, verification_token)

    response = {
            "status": True,
            "message": "User created successfully, check your email for verification",
            "data": {
                "user": {
                    "id": str(db_user.id),
                    "email": db_user.email,
                    "is_email_verified": db_user.is_email_verified,
                    "created_at": db_user.created_at.isoformat(),
                    "updated_at": db_user.updated_at.isoformat()
                }
            },
        }
    print("The response before the verification is:", response)
    return RegisterResponseModel(**response)



@router.post("/verify-email/", include_in_schema=True)
async def verify_email(token: str = Query(...),  db: Session = Depends(get_db)):
    print("The token is", token)
    user = db.query(User).filter(User.verification_token == token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.is_email_verified = True
    user.verification_token = None 
    db.commit()

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        user=user, expires_delta=access_token_expires
    )
    response = {
            "status": True,
            "message": "User created successfully",
            "data": {
                "user": {
                    "email": user.email,
                    "id": str(user.id),
                    "is_email_verified": user.is_email_verified,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat()
                }
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    return LoginResponseModel(**response)


@router.post("/signin/", response_model=LoginResponseModel)
async def login_for_access_token(
    form_data: LoginRequestModel, db: Session = Depends(get_db)
):
    """
        Login a user.
        If the email and password are correct, it will return the user data and access token.
        If the email and password are incorrect, it will raise a 401 error.
    """
    user = authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not_verified_user(db, form_data.email):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified, Please verify your email to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        user=user, expires_delta=access_token_expires
    )

    response_data = {
        "status": True,
        "message": "User login successful",
        "data": {
            "user": {
                "email": user.email,
                "id": str(user.id),
                "is_email_verified": user.is_email_verified,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat()
            },
        },
        "access_token": access_token,
        "token_type": "bearer"
    }
    return LoginResponseModel(**response_data)



@router.get("/signin/google/")
async def google_login(request: Request):
    """
        Redirect the user to Google login page.
        if authenticated, return success else raise a 400 error.
    """
    print("The request is", request.headers.get("Referer"))
    redirect_uri = request.url_for('auth')
    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=openid email profile"

    return RedirectResponse(url=google_auth_url)

@router.get("/auth", include_in_schema=False)
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
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
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
            CLIENT_ID,
            clock_skew_in_seconds=2
        )

        payload: GooglePayload = {
            "sub": id_info.get('sub'),
            "email": id_info.get('email'),
            "name": id_info.get('name'),
            "picture": id_info.get('picture'),
            "is_email_verified": id_info.get('email_verified'),
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





@router.get("/users/me/")
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return current_user

# delete account
@router.delete("/users/delete_me/")
async def delete_user(current_user: UserInDB = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == current_user.email).first()
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.post("/users/request-email-verification/", response_model=RegisterResponseModel, include_in_schema=True)
async def get_token_to_verify_email( form_data: GetTokenRequest):
    """
        If a users email is not verified, generate a token and send a verification email.
        This is only used when a user tries to login with an email and their email has not been verified.
    """
    db = SessionLocal()
    existing_user = authenticate_google_user(db, form_data.email)
    if not existing_user:
        raise HTTPException(status_code=400, detail="Email not registered. Please signup")
    if not not_verified_user(db, form_data.email):
        raise HTTPException(status_code=400, detail="Email already verified. Please signin")
    
    verification_token = str(uuid.uuid4()) 
    existing_user.verification_token = verification_token
    db.commit()


    print(f"Generated Token for {existing_user.email}: {verification_token}")
    print(f"Stored Token in DB: {existing_user.verification_token}")
    send_verification_email(existing_user.email, verification_token)

    response = {
            "status": True,
            "message": "Token created successfully, check your email for verification",
            "data": {
                "user": {
                    "id": str(existing_user.id),
                    "email": existing_user.email,
                    "is_email_verified": existing_user.is_email_verified,
                    "created_at": existing_user.created_at.isoformat(),
                    "updated_at": existing_user.updated_at.isoformat()
                }
            },
        }
    print("The response before the verification is:", response)
    return RegisterResponseModel(**response)



async def validate(request: Request):
    user_data = request.session.get('user_data')
    print("The user data is", user_data)
    db = SessionLocal()
    if not user_data or "email" not in user_data:
        raise HTTPException(status_code=401, detail="User not authenticated")
    try:
        user = await authenticate_google_user(db, user_data["email"]) 
        print("The user from the validate function", user)
        if user:
            print("Following the path of existing user")
        else:
            print("Following the path of new user")
            user = await add_google_user(db, user_data) 

        if not user:
            raise HTTPException(status_code=500, detail="User creation failed")
        
        access_token_expires = timedelta(minutes=30)
        print("The user going into the access token is ", user)
        access_token = create_access_token(
            user=user, expires_delta=access_token_expires
        )

        frontend_redirect_url = f"http://localhost:3000"
        
        return RedirectResponse(
            url=frontend_redirect_url,
            headers={
                "Set-Cookie": f"access_token={access_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=1800",
            },
            status_code=302,
        )

    except Exception as e:
        print("The error is", e)
        raise HTTPException(status_code=500, detail=f"Internal Server Error, {e}")



#     # ✅ Set secure HTTP-only cookie
#     response.set_cookie(
#         key="access_token",
#         value=access_token,
#         httponly=True,
#         secure=not IS_DEV,
#         samesite="Lax"
#         max_age=1800
#     )

#     return response


# key="access_token",
# value=access_token,
# httponly=True,  # Prevents JavaScript access
# secure=True,  # Only send over HTTPS
# samesite="Strict",  # Prevents CSRF
# max_age=1800  # 30 minutes





# Get redirect path from query params (default to home "/")
# redirect_path = request.query_params.get("redirect", "/")

# # Ensure the redirect path is safe
# if not redirect_path.startswith("/"):
#     raise HTTPException(status_code=400, detail="Invalid redirect path")

# frontend_redirect_url = f"http://localhost:3000{redirect_path}"
