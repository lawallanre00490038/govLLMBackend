from fastapi import FastAPI, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi import Request
from .database import engine, Base, get_db
from .models import User
from fastapi.middleware.cors import CORSMiddleware
from .schemas import  UserInDB, LoginResponseModel, RegisterResponseModel, LoginRequestModel
from .auth import authenticate_user, create_access_token, get_current_active_user, get_password_hash
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

Base.metadata.create_all(bind=engine)
google_client = os.getenv("GOOGLE_CLIENT_ID")
google_secret = os.getenv("GOOGLE_CLIENT_SECRET")
secret_key = os.environ.get("SECRET_KEY")

print("The secret is:",  secret_key)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=secret_key, same_site="lax", https_only=False)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)


# Google OAuth Setup
oauth = OAuth()
oauth.register(
    name="google",
    client_id=google_client,
    client_secret=google_secret,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    authorize_params={"response_type": "id_token token", "scope": "openid email profile"},
    client_kwargs={"scope": "openid email profile"},
    state_generator=lambda: "random_state_here", 
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration"
)



@app.get("/")
async def root():
    return {"message": "Hello World"}



@app.post("/register/", response_model=RegisterResponseModel)
async def register_user(user: UserInDB, db: Session = Depends(get_db)):
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



@app.post("/login", response_model=LoginResponseModel)
async def login_for_access_token(
    form_data: LoginRequestModel, db: Session = Depends(get_db)
):
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



@app.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_auth_callback") 
    print("Redirect URI:", redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri)

# @app.get("/auth/google/callback")
# async def google_auth_callback(request: Request, db: Session = Depends(get_db)):
#     token = await oauth.google.authorize_access_token(request)
#     # user_info = token.get("userinfo")
#     user_info = await oauth.google.parse_id_token(request, token)
#     print(user_info)

#     if not user_info:
#         raise HTTPException(status_code=400, detail="Failed to retrieve user information")

#     # Check if user already exists
#     user = db.query(User).filter(User.email == user_info["email"]).first()
#     if not user:
#         # Register the user if not found
#         new_user = User(
#             email=user_info["email"],
#             password="", 
#             email_verified=True
#         )
#         db.add(new_user)
#         db.commit()
#         db.refresh(new_user)
#         user = new_user

#     access_token = create_access_token(data={"sub": user.email})

#     return {
#         "status": True,
#         "message": "User login successful via Google",
#         "data": {
#             "user": {
#                 "email": user.email,
#                 "id": str(user.id),
#                 "email_verified": user.email_verified,
#                 "created_at": user.created_at.isoformat() if hasattr(user, "created_at") else None,
#                 "updated_at": user.updated_at.isoformat() if hasattr(user, "updated_at") else None
#             },
#             "access_token": access_token,
#             "token_type": "bearer"
#         }
#     }

@app.get("/auth/google/callback")
async def google_auth_callback(request: Request, db: Session = Depends(get_db)):
    print("Received request:", request.query_params)
    token = await oauth.google.authorize_access_token(request)
    print("OAuth Token Response:", token)

    if "id_token" in token:
        user_info = await oauth.google.parse_id_token(request, token)
    else:
        # Fallback: Manually fetch user info
        resp = await oauth.google.get("https://www.googleapis.com/oauth2/v1/userinfo", token=token)
        user_info = resp.json()

    print("User Info:", user_info)

    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to retrieve user information")

    user = db.query(User).filter(User.email == user_info["email"]).first()
    if not user:
        new_user = User(email=user_info["email"], password="", email_verified=True)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user

    access_token = create_access_token(data={"sub": user.email})

    return {
        "status": True,
        "message": "User login successful via Google",
        "data": {
            "user": {
                "email": user.email,
                "id": str(user.id),
                "email_verified": user.email_verified,
                "created_at": user.created_at.isoformat() if hasattr(user, "created_at") else None,
                "updated_at": user.updated_at.isoformat() if hasattr(user, "updated_at") else None
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    }


@app.get("/users/me/")
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return current_user
