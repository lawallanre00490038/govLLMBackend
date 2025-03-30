from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError
from src.db.database import SessionLocal
from src.models.user import User
from src.users.schemas import TokenData, UserInDB
from src.configs.config import SECRET_KEY


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, password):
    return pwd_context.verify(plain_password, password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        return None
    return user

def not_verified_user(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user.is_email_verified:
        return True
    return False

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=35))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user: User, expires_delta: timedelta | None = None):
    to_encode = {
        "sub": user.email,
        "id": str(user.id),
        "is_email_verified": user.is_email_verified,
        "exp": datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=35))
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Google OAuth2 login and registration
async def authenticate_google_user(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    return user
async def add_google_user(db: Session, user_data: dict):
    user = User(
        email=user_data["email"],
        verification_token=user_data["verification_token"],
        is_email_verified=user_data["is_email_verified"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
