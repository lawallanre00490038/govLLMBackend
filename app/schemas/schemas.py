from pydantic import BaseModel
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    email: str | None = None
    # disabled: bool | None = None

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    password: str



# User response model
class UserModel(BaseModel):
    email: str
    id: UUID
    is_email_verified: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class LoginRequestModel(BaseModel):
    email: str
    password: str


class DataModel(BaseModel):
    user: UserModel

class LoginResponseModel(BaseModel):
    status: bool
    message: str
    data: DataModel
    access_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True

class RegisterResponseModel(BaseModel):
    status: bool = True
    message: str = "Request successful"
    data: DataModel
    

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    
class GooglePayload(BaseModel):
    sub: Optional[Any] = None
    name: str
    picture: str
    is_email_verified: bool


class GetTokenRequest(BaseModel):
    email: str
    
class GetTokenResponse(BaseModel):
    status: bool
    message: str
    data: TokenData