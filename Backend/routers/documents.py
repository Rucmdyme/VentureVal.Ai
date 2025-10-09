# Document processing

# routers/documents.py
from fastapi import APIRouter, Request
from models.schemas import DocumentUploadRequest, DocumentDetailsRequest
from services import document_processor
from utils.auth_utils import require_user_or_none
from exceptions import UnAuthorizedException
from typing import List

router = APIRouter()

@router.post("/generate-upload-url")
@require_user_or_none
async def _generate_upload_url(request: Request, payload: DocumentUploadRequest, user_info=None):
    """
    Generate a V4 signed URL for uploading a file directly to Firebase Storage.
    Supports file types: pitch_deck, call_transcript, founder_update, email_communication
    Supports extensions: .pdf, .txt, .jpg, .jpeg, .png (Max 1 file)
    """
    user_id = None
    if user_info:
        user_id = user_info["user_id"]
    data = await document_processor.DocumentService().generate_presigned_url(payload, user_id)
    return data
       

@router.post("/")
@require_user_or_none
async def _get_document_details(request: Request, payload: DocumentDetailsRequest, idtoken: str = None, user_info=None,):
    """Download file link from Firebase Storage"""
    if not user_info or not user_info.get("user_id"):
        raise UnAuthorizedException
    user_id = user_info["user_id"]
    file_record = await document_processor.DocumentService().get_document_details(payload.document_id, user_id, payload.analysis_id, payload.is_download_url_required)
    return {"data": file_record, "success": True}
