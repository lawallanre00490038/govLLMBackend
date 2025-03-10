from pydantic import BaseModel
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


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
    email_verified: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LoginRequestModel(BaseModel):
    email: str
    password: str

class LoginResponseModel(BaseModel):
    status: bool = True
    message: str = "User login successful"
    data: dict

    class Config:
        orm_mode = True

class RegisterResponseModel(BaseModel):
    status: bool = True
    message: str = "Request successful"
    data: dict | list | str | int | float | bool | None = None

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None