from fastapi import APIRouter, FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import httpx

from sqlalchemy.orm import Session
from datetime import timedelta
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from .config import CLIENT_ID, CLIENT_SECRET, SECRET_KEY
from google.oauth2 import id_token
from google.auth.transport import requests

from .database import engine, Base, get_db, SessionLocal
from .models import User
from fastapi.middleware.cors import CORSMiddleware
from .schemas import  UserInDB, LoginResponseModel, RegisterResponseModel, LoginRequestModel, GooglePayload
from .auth import authenticate_user, create_access_token, get_current_active_user, get_password_hash, authenticate_google_user, add_google_user


from dotenv import load_dotenv

Base.metadata.create_all(bind=engine)
load_dotenv()

app = FastAPI()
router = APIRouter()


oauth = OAuth()

# Allow requests from your frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://yourfrontend.com",
    "https://govllmbackend.onrender.com"
]
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)


@router.get("/home")
async def home(request: Request):
    user_data = request.session.get("user_data")
    if not user_data:
        return {"message": "No session data, user not authenticated"}
    
    return {"message": "User is authenticated", "user_data": user_data}

@router.post("/register/", response_model=RegisterResponseModel)
async def register_user(user: UserInDB, db: Session = Depends(get_db)):
    """
        Register a new user.
        If the email already exists, it will raise a 400 error.
        If the registration is successful, it will return the user data.
    """
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = User(
        email=user.email,
        password=get_password_hash(user.password),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {
        "status": True,
        "message": "User created successfully",
        "data": {
            "user": {
                "email": db_user.email,
                "id": str(db_user.id),
                "email_verified": getattr(db_user, "email_verified", False),
                "created_at": db_user.created_at.isoformat() if hasattr(db_user, "created_at") else None,
                "updated_at": db_user.updated_at.isoformat() if hasattr(db_user, "updated_at") else None
            }
        }
    }



@router.post("/login", response_model=LoginResponseModel)
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

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    response_data = {
        "status": True,
        "message": "User login successful",
        "data": {
            "user": {
                "email": user.email,
                "id": str(user.id),
                "email_verified": getattr(user, "email_verified", False),
                "created_at": user.created_at.isoformat() if hasattr(user, "created_at") else None,
                "updated_at": user.updated_at.isoformat() if hasattr(user, "updated_at") else None
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    }
    return LoginResponseModel(**response_data)



@router.get("/login/google")
async def google_login(request: Request):
    """
        Redirect the user to Google login page.
    """
    redirect_uri = request.url_for('auth')
    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=openid email profile"

    return RedirectResponse(url=google_auth_url)

@router.get("/auth")
async def auth(code: str, request: Request):
    """
        Handle the Google login callback.
        Responsible for exchanging the code for an access token and validating the token.
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
            "email_verified": id_info.get('email_verified'),
        }

        request.session["user_data"] = payload 
        return RedirectResponse(url=request.url_for('token'))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid id_token: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/token")
async def token(request: Request):
    """
        Handle the Google login callback.
        If the login is successful, it will return the user data and access token.
        If the login is not successful, it will raise a 400 error.
    """
    user_data = request.session.get('user_data')
    db = SessionLocal()
    if not user_data:
        raise HTTPException(status_code=401, detail="User not authenticated")
    try:
        user =  authenticate_google_user(db, user_data["email"])
        if user:
            print("Following the path of existing user")
        else:
            print("Following the path of new user")
            add_google_user(db, user_data["email"])
            user =  authenticate_google_user(db, user_data["email"])
        
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user_data["email"]}, expires_delta=access_token_expires
        )
        response_data = {
            "status": True,
            "message": "User login successful",
            "data": {
                "user": {
                    "email": user.email,
                    "id": str(user.id),
                    "email_verified": getattr(user, "email_verified", False),
                    "created_at": user.created_at.isoformat() if hasattr(user, "created_at") else None,
                    "updated_at": user.updated_at.isoformat() if hasattr(user, "updated_at") else None
                },
                "access_token": access_token,
                "token_type": "bearer"
            }
            }
        # print(LoginResponseModel(**response_data))
        # return RedirectResponse(url=request.url_for('home')) 
        return LoginResponseModel(**response_data)
    except Exception as e:
        print("The error is", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/users/me/")
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return current_user


app.include_router(router, prefix="/api/authentication", tags=["auth"])
