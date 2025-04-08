from firebase_admin import auth
import firebase_admin
from firebase_admin import credentials, auth


# # Replace with your actual details
# cred = credentials.Certificate({
#     "type": "service_account",
#     "project_id": "govllimner",
#     "private_key_id": "<YOUR_PRIVATE_KEY_ID>",
#     "private_key": "-----BEGIN PRIVATE KEY-----<KEY>-----END PRIVATE KEY-----\n",
#     "client_email": "foo@govllimner.iam.gserviceaccount.com",
#     "client_id": "<YOUR_CLIENT_ID>",
#     "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#     "token_uri": "https://oauth2.googleapis.com/token",
#     "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#     "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/foo%40govllimner.iam.gserviceaccount.com"
# })

# firebase_admin.initialize_app(cred, {
#     'databaseURL': 'https://govllimner.firebaseio.com'
# })


cred = credentials.Certificate("../keys/gov.json")
firebase_admin.initialize_app(cred)

async def send_verification_email(to_email: str):
    """
    Send verification email using Firebase Authentication.
    """
    try:
        # Create a user in Firebase Authentication (if not already created)
        user = auth.get_user_by_email(to_email)
    except auth.UserNotFoundError:
        user = auth.create_user(email=to_email)

    # Generate email verification link
    verification_link = auth.generate_email_verification_link(to_email)

    # Send the verification link to the user's email (via your custom SMTP or frontend)
    print(f"Verification link sent to {to_email}: {verification_link}")
