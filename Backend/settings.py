from os import getenv
from dotenv import load_dotenv
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

CRED_PATH = getenv("GOOGLE_APPLICATION_CREDENTIALS")
BUCKET_ID = getenv("BUCKET_ID")
PROJECT_ID = getenv("PROJECT_ID")
GCP_REGION = getenv("GCP_REGION")