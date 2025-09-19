from os import getenv
from dotenv import load_dotenv
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

BUCKET_ID = getenv("BUCKET_ID")
PROJECT_ID = getenv("PROJECT_ID")
GCP_REGION = getenv("GCP_REGION")
FIREBASE_CONFIG_JSON = getenv("FIREBASE_CONFIG_JSON")