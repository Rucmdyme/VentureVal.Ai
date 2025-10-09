# Analysis endpoints

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
import logging

from models.schemas import AnalysisRequest, AnalysisResponse
from utils.auth_utils import require_user_or_none
from utils.ai_client import monitor_usage
from services.analysis_service import AnalysisService
from exceptions import UnAuthorizedException, NotFoundException, ServerException

logger = logging.getLogger(__name__)

router = APIRouter()

def get_analysis_service():
    return AnalysisService()


@router.post("/start", response_model=AnalysisResponse)
@require_user_or_none
@monitor_usage("document_processing")
async def start_analysis(
    request: Request, 
    payload: AnalysisRequest,
    background_tasks: BackgroundTasks,
    user_info=None,
    analysis_service: AnalysisService = Depends(get_analysis_service),
):
    """Start new startup analysis"""
    user_id = user_info["user_id"] if user_info else None
    
    try:
        analysis_id, storage_paths = await analysis_service.create_analysis_session(payload, user_id)
        
        # Start background processing
        background_tasks.add_task(analysis_service.process_analysis_safe, analysis_id, payload, storage_paths)
        
        return AnalysisResponse(
            analysis_id=analysis_id,
            status="processing",
            message="Analysis started. Check status for updates."
        )

    except Exception as e:
        logger.error(f"Unexpected error in start_analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{analysis_id}")
@require_user_or_none
async def get_analysis(
    request: Request, 
    analysis_id: str, 
    idtoken: str = None, 
    user_info=None,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Get analysis results"""
    if user_info:
        from utils.helpers import match_user_and_analysis_id
        analysis_user_details = await match_user_and_analysis_id(user_info["user_id"], analysis_id)
        if not analysis_user_details:
            raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        return await analysis_service.fetch_analysis_data(analysis_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServerException as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/{analysis_id}/reweight")
async def update_weighting(
    analysis_id: str, 
    weighting_config: dict,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Recalculate scores with new weightings"""
    try:
        return await analysis_service.update_weighting(analysis_id, weighting_config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update weighting for {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update weighting")

@router.post("/bulk-details")
@require_user_or_none
async def get_bulk_analysis(
    request: Request, 
    idtoken: str = None, 
    user_info=None,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Get bulk analysis data for authenticated user"""
    if not user_info or not user_info.get("user_id"):
        raise UnAuthorizedException
    
    user_id = user_info["user_id"]
    try:
        return await analysis_service.get_bulk_analysis(user_id)
    except ServerException:
        raise
    except Exception as error:
        logger.error(f"Unexpected error in bulk analysis: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis data")

@router.delete("/delete/{analysis_id}")
@require_user_or_none
async def delete_analysis(
    request: Request, 
    analysis_id: str, 
    idtoken: str = None, 
    user_info=None,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """Delete an analysis for authenticated user"""
    if not user_info or not user_info.get("user_id"):
        raise UnAuthorizedException
    
    user_id = user_info["user_id"]
    try:
        return await analysis_service.delete_analysis(analysis_id, user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServerException:
        raise
    except Exception as error:
        logger.error(f"Unexpected error in delete analysis: {error}")
        raise HTTPException(status_code=500, detail="Failed to delete analysis")

