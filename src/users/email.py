from __future__ import print_function
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from src.config import settings
from typing import Optional
import resend


def send_verification_email(to_email: str, verification_token: str):
    print("Sending verification email to: ", to_email)
    print("The verification token is: ", verification_token)
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    verification_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"

    sender = {"name": "GovLLMiner", "email": settings.EMAIL_FROM}
    to = [{"email": to_email}]
    
    subject = "Verify Your Email Address"
    html_content = f"""
        <html>
            <body>
                <h2>Email Verification</h2>
                <p>Click the link below to verify your email address:</p>
                <a href="{verification_link}">Verify Email</a>
                <p>If you did not request this, please ignore this email.</p>
            </body>
        </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=to,
        subject=subject,
        html_content=html_content
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(api_response)
    except ApiException as e:
        print(f"Exception when calling SMTPApi->send_transac_email: {e}\n")




def send_reset_password_email(to_email: str, reset_token: str):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"

    sender = {"name": "AIforGoV", "email": settings.EMAIL_FROM}
    to = [{"email": to_email}]
    
    subject = "Reset Your Password"
    html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>We received a request to reset your password. Click the link below to continue:</p>
                <a href="{reset_link}">Reset Password</a>
                <p>This link will expire after a short period.</p>
                <p>If you didn’t request a password reset, you can safely ignore this email.</p>
            </body>
        </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=to,
        subject=subject,
        html_content=html_content
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(api_response)
    except ApiException as e:
        print(f"Exception when calling SMTPApi->send_transac_email: {e}\n")



resend.api_key = settings.RESEND_API_KEY
def send_verification_email_resend(to_email: str, verification_token: str):
    print("Sending verification email to: ", to_email)
    print("The verification token is: ", verification_token)

    verification_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"

    sender = "GovLLMiner <no-reply@equalyz.ai>"
    subject = "GovLLMiner: Verify Your Email Address"
    
    html_content = f"""
        <html>
            <body>
                <h2>Email Verification</h2>
                <p>Click the link below to verify your email address:</p>
                <a href="{verification_link}">Verify Email</a>
                <p>If you did not request this, please ignore this email.</p>
            </body>
        </html>
    """
    try:
        response = resend.Emails.send({
            "from": sender,
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        print("Email sent successfully: ", response)
    except Exception as e:
        print(f"Exception when sending email: {e}\n")



def send_reset_password_email_resend(to_email: str, reset_token: str):
    reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"

    sender = "GovLLMiner <no-reply@equalyz.ai>"
    subject = "GovLLMiner: Reset Your Password"

    html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>We received a request to reset your password. Click the link below to continue:</p>
                <a href="{reset_link}">Reset Password</a>
                <p>This link will expire after a short period.</p>
                <p>If you didn’t request a password reset, you can safely ignore this email.</p>
            </body>
        </html>
    """
    try:
        response = resend.Emails.send({
            "from": sender,
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        print("Email sent successfully: ", response)
    except Exception as e:
        print(f"Exception when sending email: {e}\n")
