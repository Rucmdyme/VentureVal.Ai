# Analysis endpoints

# routers/analysis.py
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from datetime import datetime
import asyncio
import logging
from typing import Dict, Any
import uuid

from models.schemas import AnalysisRequest, AnalysisResponse
from models.database import get_firestore_client
from services.document_processor import DocumentProcessor
from services.risk_analyzer import RiskAnalyzer
from services.benchmark_engine import BenchmarkEngine
from services.deal_generator import DealNoteGenerator
from services.weighting_calculator import WeightingCalculator
from utils.ai_client import monitor_usage
from utils.helpers import update_progress
from utils.enhanced_text_cleaner import sanitize_for_frontend, clean_response_dict, clean_response_text

logger = logging.getLogger(__name__)

router = APIRouter()

def get_document_processor():
    return DocumentProcessor()

def get_risk_analyzer():
    return RiskAnalyzer()

def get_benchmark_engine():
    return BenchmarkEngine()

def get_deal_generator():
    return DealNoteGenerator()

def get_weighting_calculator():
    return WeightingCalculator()


@router.post("/start", response_model=AnalysisResponse)
@monitor_usage("document_processing")
async def start_analysis(
    request: AnalysisRequest, 
    background_tasks: BackgroundTasks,
    firestore_client=Depends(get_firestore_client)
):
    """Start new startup analysis"""
    
    try:
        if not request.storage_paths:
            raise HTTPException(status_code=400, detail="At least one storage path is required")
        # Create analysis session
        analysis_id = f"analysis_{uuid.uuid4().hex}"
        
        # Store initial session
        analysis_doc = {
            'id': analysis_id,
            'status': 'processing',
            'company_name': request.company_name or 'Unknown',
            'storage_paths': request.storage_paths,
            'weighting_config': request.weighting_config.model_dump() if request.weighting_config else None,
            'created_at': datetime.now(),
            'progress': 0,
            'progress_message': 'Analysis initiated',
            'error': None
        }

        try:
            doc_ref = firestore_client.collection('analyses').document(analysis_id)
            await asyncio.get_event_loop().run_in_executor(
                None, 
                doc_ref.set,
                analysis_doc
            )
        except Exception as db_error:
            logger.error(f"Failed to create analysis record: {db_error}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to initialize analysis"
            )

        # Start background processing
        background_tasks.add_task(process_analysis_safe, analysis_id, request)
        
        return AnalysisResponse(
            analysis_id=analysis_id,
            status="processing",
            message="Analysis started. Check status for updates."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in start_analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_analysis_safe(analysis_id: str, request: AnalysisRequest):
    """Safe wrapper for analysis processing with comprehensive error handling"""
    try:
        await process_analysis(analysis_id, request)
    except Exception as e:
        logger.error(f"Critical error in background analysis {analysis_id}: {e}")
        # Ensure error state is recorded even if process_analysis fails completely
        try:
            firestore_client = get_firestore_client()
            error_update = {
                'status': 'failed',
                'error': f"Critical processing error: {str(e)}",
                'failed_at': datetime.now(),
                'progress_message': f'Analysis failed: {str(e)}'
            }
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: firestore_client.collection('analyses').document(analysis_id).update(error_update)
            )
        except Exception as update_error:
            logger.critical(f"Failed to record critical error for {analysis_id}: {update_error}")


async def process_analysis(analysis_id: str, request: AnalysisRequest):
    """Background task for analysis processing with improved error handling"""
    
    # Get service instances
    doc_processor = get_document_processor()
    risk_analyzer = get_risk_analyzer()
    benchmark_engine = get_benchmark_engine()
    deal_generator = get_deal_generator()
    weighting_calc = get_weighting_calculator()
    
    try:
        # Step 1: Document Processing
        await update_progress(analysis_id, 21, "Processing documents...")
        
        try:
            processed_data = await doc_processor.process_documents_from_storage(request.storage_paths)
        except Exception as e:
            await update_progress(status = "failed", error=f"Document processing failed: {str(e)}")
            raise ValueError(f"Document processing failed: {str(e)}")
        if not processed_data:
            raise ValueError("Document processing failed - no synthesized data extracted")

        if 'error' in processed_data:
            logger.error(f"Document processing error: {processed_data['error']}")
            raise ValueError(f"Document processing failed: {processed_data['error']}")
        
        # Validate processed data
        if not processed_data or 'synthesized_data' not in processed_data:
            raise ValueError("Document processing failed - no synthesized data extracted")
            
        await update_progress(analysis_id, 30, "Documents processed")
        
        synthesized_data = processed_data['synthesized_data']
        
        # Step 2: Risk Analysis
        await update_progress(analysis_id, 40, "Analyzing risks...")
        try:
            risk_results = await risk_analyzer.analyze_risks(synthesized_data)
        except Exception as e:
            raise ValueError(f"Risk analysis failed: {str(e)}")
            
        await update_progress(analysis_id, 55, "Risk assessment complete")
        
        # Step 3: Benchmarking
        await update_progress(analysis_id, 60, "Running benchmarks...")
        sector = synthesized_data.get('sector', 'unknown')
        try:
            benchmark_results = await benchmark_engine.calculate_percentiles(
                synthesized_data, 
                sector
            )
        except Exception as e:
            raise ValueError(f"Benchmarking failed: {str(e)}")
            
        await update_progress(analysis_id, 75, "Benchmarking complete")
        
        # Step 4: Weighted Scoring
        await update_progress(analysis_id, 80, "Calculating scores...")
        weighting_config = request.weighting_config.model_dump() if request.weighting_config else {}
        try:
            weighted_scores = await weighting_calc.calculate_weighted_score(
                analysis_id,
                synthesized_data,
                risk_results,
                benchmark_results,
                weighting_config
            )
        except Exception as e:
            raise ValueError(f"Score calculation failed: {str(e)}")
            
        await update_progress(analysis_id, 90, "Scoring complete")
        
        # Step 5: Deal Note Generation
        await update_progress(analysis_id, 95, "Generating deal note...")
        try:
            deal_note = await deal_generator.generate_deal_note(
                synthesized_data,
                risk_results,
                benchmark_results,
                weighted_scores
            )
        except Exception as e:
            logger.warning(f"Deal note generation failed for {analysis_id}: {e}")
            deal_note = {"error": "Deal note generation failed", "details": str(e)}
            
        await update_progress(analysis_id, 100, "Analysis complete")
        
        # Store final results
        final_results = {
            'status': 'completed',
            'processed_data': processed_data,
            'risk_assessment': risk_results,
            'benchmarking': benchmark_results,
            'weighted_scores': weighted_scores,
            'deal_note': deal_note,
            'completed_at': datetime.now(),
            'progress': 100,
            'progress_message': 'Analysis completed successfully',
            'error': None
        }
        
        firestore_client = get_firestore_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: firestore_client.collection('analyses').document(analysis_id).update(final_results)
        )
        
        logger.info(f"Analysis {analysis_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {e}")
        # Update with error status
        error_update = {
            'status': 'failed',
            'error': str(e),
            'failed_at': datetime.now(),
            'progress_message': f'Analysis failed: {str(e)}'
        }
        
        try:
            firestore_client = get_firestore_client()
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: firestore_client.collection('analyses').document(analysis_id).update(error_update)
            )
        except Exception as update_error:
            logger.critical(f"Failed to update error status for {analysis_id}: {update_error}")


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get analysis results"""
    
    try:
        # Use async executor for Firestore operation
        firestore_client = get_firestore_client()
        doc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: firestore_client.collection('analyses').document(analysis_id).get()
        )
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        data = doc.to_dict()
        
        data = serialize_datetime_fields(data)
        
        return sanitize_for_frontend(data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analysis: {str(e)}")

@router.post("/{analysis_id}/reweight")
async def update_weighting(
    analysis_id: str, 
    weighting_config: dict,
    firestore_client=Depends(get_firestore_client),
    weighting_calc: WeightingCalculator = Depends(get_weighting_calculator)
):
    """Recalculate scores with new weightings"""

    if not analysis_id or not analysis_id.startswith('analysis_'):
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")
    
    # Validate weighting_config
    if not weighting_config or not isinstance(weighting_config, dict):
        raise HTTPException(
            status_code=400, 
            detail="Valid weighting configuration is required"
        )
    
    try:
        doc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: firestore_client.collection('analyses').document(analysis_id).get()
        )
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis_data = doc.to_dict()
        current_status = analysis_data.get('status', 'unknown')
        if current_status != 'completed':
            raise HTTPException(
                status_code=400, 
                detail=f"Analysis not completed yet. Current status: {current_status}"
            )
        
        # Validate required data exists
        required_keys = ['processed_data', 'risk_assessment', 'benchmarking']
        missing_keys = [key for key in required_keys if key not in analysis_data]
        if missing_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Analysis data incomplete. Missing: {', '.join(missing_keys)}"
            )
        
        # Recalculate with new weights
        try:
            synthesized_data = analysis_data['processed_data']['synthesized_data']
        except (KeyError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Processed data structure is invalid"
            )
        
        # Recalculate with new weights
        try:
            new_scores = await weighting_calc.calculate_weighted_score(
                analysis_id,
                synthesized_data,
                analysis_data['risk_assessment'],
                analysis_data['benchmarking'],
                weighting_config
            )
        except Exception as e:
            logger.error(f"Reweighting failed for {analysis_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to recalculate scores with new weights"
            )
        
        # Update stored results
        update_data = {
            'weighted_scores': new_scores,
            'weighting_config': weighting_config,
            'updated_at': datetime.now()
        }
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: firestore_client.collection('analyses').document(analysis_id).update(update_data)
        )
        
        logger.info(f"Weighting updated successfully for {analysis_id}")
        
        return {
            "message": "Weighting updated successfully",
            "analysis_id": analysis_id,
            "new_scores": new_scores
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update weighting for {analysis_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to update weighting"
        )

def serialize_datetime_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively convert datetime objects to ISO strings"""
    if isinstance(data, dict):
        return {
            key: serialize_datetime_fields(value) 
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [serialize_datetime_fields(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data