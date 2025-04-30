from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional
from sqlmodel import select, Session
from src.db.models import User
from src.errors import UserAlreadyExists, InvalidCredentials, EmailAlreadyVerified, ResetPasswordFailed, AccountNotVerified
from .schemas import UserCreateModel, VerificationMailSchemaResponse, ResetPasswordSchemaResponseModel, ResetPasswordModel, ForgotPasswordModel
from .auth import generate_passwd_hash, verify_password
from .email import send_verification_email, send_reset_password_email, send_verification_email_resend, send_reset_password_email_resend
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

    async def create_user(self, user_data: UserCreateModel, session: AsyncSession, is_google: Optional[bool] = False):
        """Create a new user in the database."""
        if await self.user_exists(user_data.email, session):
            raise UserAlreadyExists()
        
        print("The data coming in: ", user_data)
        
        try:
            verification_token = str(uuid.uuid4()) 
            hash_password = generate_passwd_hash(user_data.password)

            new_user = User(
                full_name=user_data.full_name,
                email=user_data.email,
                password=hash_password,
                is_verified=True if is_google else False,
                verification_token=verification_token
            )

            session.add(new_user)
            await session.commit()

            if not is_google:
                # send_verification_email(new_user.email, verification_token)
                send_verification_email_resend(new_user.email, verification_token)

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
        if not user.is_verified:
            raise AccountNotVerified()
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
    
        
    async def delete_user(self, user: User, session: AsyncSession) -> None:
        """Delete a user from the database."""
        statement = select(User).where(User.id == user.id)
        result = await session.execute(statement)
        db_user = result.scalar_one_or_none()

        if db_user:
            await session.delete(db_user)
            await session.commit()
            return None
        else:
            raise InvalidCredentials()
        
    # resend verification email
    async def resend_verification_email(self, email: str, session: AsyncSession) -> VerificationMailSchemaResponse:
        """Resend the verification email to the user."""
        try:
            user = await self.get_user_by_email(email, session)
            if user:
                if user.is_verified:
                    raise EmailAlreadyVerified()
                verification_token = str(uuid.uuid4())
                user.verification_token = verification_token
                session.add(user)
                await session.commit()
                # send_verification_email(user.email, verification_token)
                send_verification_email_resend(user.email, verification_token)
            else:
                raise InvalidCredentials()
            return VerificationMailSchemaResponse(
                status=True,
                message="Verification email sent successfully",
                verification_token=verification_token
            )
        except Exception as e:
            await session.rollback()
            raise e


     
    async def reset_password(self, user: User, payload: ResetPasswordModel, session: AsyncSession) -> ResetPasswordSchemaResponseModel:
        """Reset the user's password"""
        try:
            # Update the user's password
            user.password = generate_passwd_hash(payload.password)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            return ResetPasswordSchemaResponseModel(
                status=True,
                message="Password reset successfully."
            )
        except Exception as e:
            await session.rollback()
            raise ResetPasswordFailed()
        

    # reset password
    async def forgot_password(self, payload: ForgotPasswordModel, session: AsyncSession) -> ResetPasswordSchemaResponseModel:
        """Initiate a password reset process by sending an email with a reset link."""
        user = await self.get_user_by_email(payload.email, session)
        if not user:
            raise InvalidCredentials()

        # Generate and assign a new reset token
        reset_token = str(uuid.uuid4())
        user.verification_token = reset_token

        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Send the reset password email
        send_reset_password_email_resend(user.email, reset_token)

        return ResetPasswordSchemaResponseModel(
            status=True,
            message="A password reset link has been sent to your email."
        )
