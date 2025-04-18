from __future__ import print_function
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from src.config import settings
from typing import Optional


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
