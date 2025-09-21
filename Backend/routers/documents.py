# Document processing

# routers/documents.py
from fastapi import APIRouter, HTTPException
import time
import uuid
from pathlib import Path
from models.schemas import DocumentUploadRequest
from models.database import get_storage_bucket
from datetime import timedelta

router = APIRouter()

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/jpg',
    'image/png'
}

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png'}

@router.post("/generate-upload-url")
async def generate_upload_url(request: DocumentUploadRequest):
    """
    Generate a V4 signed URL for uploading a file directly to Firebase Storage.
    Supports file types: pitch_deck, call_transcript, founder_update, email_communication
    Supports extensions: .pdf, .docx, .txt, .jpg, .jpeg, .png (Max 1 file)
    """
    try:
        # Step 1: Validate the file metadata from the request
        file_extension = Path(request.filename).suffix.lower()
        # if request.content_type not in ALLOWED_MIME_TYPES:
        #     raise HTTPException(
        #         status_code=400, 
        #         detail=f"Invalid file type: {request.content_type}. Supported types: .pdf, .docx, .txt, .jpg, .jpeg, .png"
        #     )
        
        # Validate file extension
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file extension: {file_extension}. Supported extensions: .pdf, .docx, .txt, .jpg, .jpeg, .png"
            )

        # Step 2: Generate a unique path in Firebase Storage
        unique_id = str(uuid.uuid4())
        timestamp = int(time.time())
        filename_without_ext = Path(request.filename).stem
        storage_path = f"documents/{request.file_type.value}/{timestamp}_{filename_without_ext}_{unique_id}{file_extension}"
        
        # Step 3: Generate the V4 Signed URL
        bucket = get_storage_bucket()
        blob = bucket.blob(storage_path)

        # The frontend MUST use a PUT request with the exact content_type specified here.
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
        )

        return {
            "success": True,
            "signed_url": signed_url,
            "storage_path": storage_path,
            "upload_id": unique_id,
            "file_type": request.file_type.value,
            "message": "Upload URL generated successfully. Use PUT to upload the file."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")