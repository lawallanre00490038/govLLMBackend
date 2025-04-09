from pydantic import BaseModel
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
from typing import List


class UserCreateModel(BaseModel):
    email: EmailStr
    password: str

    class Config:
        from_attributes = True

# User login model
class UserLoginModel(BaseModel):
    email: EmailStr
    password: str

    class Config:
        from_attributes = True

# User response model
class UserModel(BaseModel):
    email: str
    id: UUID
    is_verified: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LoginResponseReadModel(BaseModel):
    status: bool
    message: str
    data: UserModel

    class Config:
        from_attributes = True

class RegisterResponseReadModel(BaseModel):
    status: bool = True
    message: str = "Request successful"
    verification_token: str
    data: UserModel
    

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None

class TokenUser(BaseModel):
    email: str
    id: UUID
    is_verified: bool
    access_token: str

    class Config:
        from_attributes = True
    
class GooglePayload(BaseModel):
    sub: Optional[Any] = None
    email: str
    name: str
    picture: str
    is_verified: bool
    verification_token: str


class GetTokenRequest(BaseModel):
    email: str

class GetTokenResponse(BaseModel):
    status: bool
    message: str
    data: TokenData


