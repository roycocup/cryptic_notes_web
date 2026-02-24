import os
import firebase_admin
from firebase_admin import credentials, firestore

# Configuration constants
SESSION_COOKIE_NAME = "mnemonic"
SESSION_MAX_AGE = 60 * 60 * 24 * 7
NOTES_SIZE_LIMIT = 60

# Security: Determine if we're running over HTTPS
# In production, set USE_HTTPS=True or detect from environment
USE_HTTPS = os.getenv("USE_HTTPS", "false").lower() == "true"

# Initialize Firebase
cred_path = os.path.join(os.path.dirname(__file__), "credentials.json")
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
else:
    # Try default credentials (for Cloud Run, etc.)
    firebase_admin.initialize_app()

db = firestore.client()
