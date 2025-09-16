# Document processing

# routers/documents.py
from fastapi import APIRouter, HTTPException
from firebase_admin import storage
import time
import uuid
from pathlib import Path
from models.schemas import DocumentUploadRequest
from models.database import get_storage_bucket

router = APIRouter()

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.doc', '.docx', '.csv', '.xls', '.xlsx'}

from datetime import timedelta

# New endpoint to generate the signed URL
@router.post("/generate-upload-url")
async def generate_upload_url(request: DocumentUploadRequest):
    """
    Generate a V4 signed URL for uploading a file directly to Firebase Storage.
    """
    try:
        # Step 1: Validate the file metadata from the request
        file_extension = Path(request.filename).suffix.lower()
        if request.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {request.content_type}")
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Invalid file extension: {file_extension}")

        # Step 2: Generate a unique path in Firebase Storage
        unique_id = str(uuid.uuid4())
        timestamp = int(time.time())
        storage_path = f"documents/{timestamp}_{unique_id}{file_extension}"
        
        # Step 3: Generate the V4 Signed URL
        bucket = get_storage_bucket()
        blob = bucket.blob(storage_path)

        # The frontend MUST use a PUT request with the exact content_type specified here.
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=request.content_type,
        )

        return {
            "success": True,
            "signed_url": signed_url,
            "storage_path": storage_path,
            "upload_id": unique_id,
            "message": "Upload URL generated successfully. Use PUT to upload the file."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")