import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', None)
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', None)
SECRET_KEY = os.environ.get('SECRET_KEY', None)

BREVO_API_KEY = os.getenv("BREVO_API_KEY", None)
SENDER_EMAIL = os.getenv("SENDER_EMAIL", None)
FRONTEND_URL = os.getenv("FRONTEND_URL", None)
EMAIL_FROM = os.getenv("EMAIL_FROM", None)
BACKEND_URL = os.getenv("BACKEND_URL", None)