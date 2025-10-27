# Firebase client

# Firebase Firestore Collections (Free Tier Limits):
# ├── users/                 # User profiles, preferences  
# ├── analysis/             # Analysis sessions, results
# ├── documents/            # Document metadata
# ├── benchmark_data/       # Static benchmark dataset
# └── weighting_profiles/   # Investor profiles

# Storage Limits (Free Tier):
# - Firestore: 1GB storage, 50K reads, 20K writes daily
# - Storage: 1GB file storage
# - Hosting: 10GB bandwidth/month

# models/database.py
import firebase_admin
from firebase_admin import credentials, firestore, storage
from settings import BUCKET_ID, FIREBASE_CONFIG_JSON
import json
# Global clients
firestore_client = None
storage_bucket = None

def init_firebase():
    """Initialize Firebase Admin SDK"""
    global firestore_client, storage_bucket
    
    try:
        # Initialize with service account key
        if not firebase_admin._apps:
            if FIREBASE_CONFIG_JSON:
                cred = credentials.Certificate(json.loads(FIREBASE_CONFIG_JSON))
            else:
                # Use default credentials in production
                cred = credentials.ApplicationDefault()
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': BUCKET_ID
            })
        
        firestore_client = firestore.client()
        storage_bucket = storage.bucket()
        
        print("Firebase initialized successfully")
        
    except Exception as e:
        print(f"Firebase initialization failed: {e}")
        raise e

def get_firestore_client():
    """Get Firestore client"""
    global firestore_client
    if firestore_client is None:
        init_firebase()
    return firestore_client

def get_storage_bucket():
    """Get Firebase Storage bucket"""
    global storage_bucket
    if storage_bucket is None:
        init_firebase()
    return storage_bucket