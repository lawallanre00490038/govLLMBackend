from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional
from sqlmodel import select, Session
from src.db.models import User
from src.errors import UserAlreadyExists, InvalidCredentials
from .schemas import UserCreateModel
from .auth import generate_passwd_hash, verify_password
from .email import send_verification_email
import uuid

class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession) -> Optional[User]:
        """Retrieve a user by their email address."""
        statement = select(User).where(User.email == email)
        user = await session.execute(statement)
        user = user.scalar_one_or_none()
        return user

    async def user_exists(self, email: str, session: AsyncSession) -> bool:
        """Check if a user with the given email already exists."""
        user = await self.get_user_by_email(email, session)
        return user is not None

    async def create_user(self, user_data: UserCreateModel, session: AsyncSession):
        user_data_dict = user_data.model_dump()
        """Create a new user in the database."""
        if await self.user_exists(user_data.email, session):
            raise UserAlreadyExists()
        
        print("The data coming in: ", user_data_dict)
        
        try:
            verification_token = str(uuid.uuid4()) 
            hash_password = generate_passwd_hash(user_data_dict["password"])

            new_user = User(
                email=user_data.email,
                password=hash_password,
                is_verified=False,
                verification_token=verification_token
            )

            session.add(new_user)
            await session.commit()
            send_verification_email(new_user.email, verification_token)

            return new_user
        except Exception as e:
            await session.rollback()
            raise e
        
    async def verify_token(self, token: str, session: AsyncSession) -> User:
        """Verify the token and retrieve the associated user."""
        result = await session.execute(select(User).where(User.verification_token == token))
        user = result.scalars().first()
        print("The user from the token is: ", user)
        if not user:
            raise InvalidCredentials()
        return user

    async def authenticate_user(self, email: str, password: str, session: AsyncSession) -> User:
        """Authenticate a user by email and password."""
        user = await self.get_user_by_email(email, session)
        print("The user from the authenticate function is: ", user)
        if not user or not verify_password(password, user.password):
            raise InvalidCredentials()
        await session.refresh(user)
        return user

    async def update_user(self, user: User, user_data: dict, session: AsyncSession) -> User:
        """Update a user's information in the database."""
        for k, v in user_data.items():
            setattr(user, k, v)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
