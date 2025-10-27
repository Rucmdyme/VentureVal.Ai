import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from models.database import get_firestore_client
from models.schemas import AnalysisRequest
from services.document_processor import DocumentProcessor
from services.risk_analyzer import RiskAnalyzer
from services.benchmark_engine import BenchmarkEngine
from services.deal_generator import DealNoteGenerator
from services.weighting_calculator import WeightingCalculator
from utils.helpers import update_progress, match_user_and_analysis_id, db_insert, db_update, db_get, asyncio_gather_dict
from utils.enhanced_text_cleaner import sanitize_for_frontend
from constants import Collections
from exceptions import NotFoundException, ServerException

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service class for handling analysis operations"""
    
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.risk_analyzer = RiskAnalyzer()
        self.benchmark_engine = BenchmarkEngine()
        self.deal_generator = DealNoteGenerator()
        self.weighting_calc = WeightingCalculator()
    
    async def map_document_id_to_analysis_id(self, document_ids: List[str], analysis_id: str) -> List[str]:
        """Map document IDs to analysis ID and return storage paths"""
        db = get_firestore_client()
        update_data = {"analysis_id": analysis_id, "updated_at": datetime.now()}
        query = db.collection(Collections.DOCUMENTS).where("document_id", "in", document_ids)
        docs_stream = await asyncio.to_thread(lambda: list(query.stream()))
        batch = db.batch()
        documents = []
            
        count = 0
        for doc in docs_stream:
            doc_data = doc.to_dict()
            documents.append(doc_data["storage_path"])
            batch.update(doc.reference, update_data)
            count += 1
            
        if count > 0:
            await asyncio.to_thread(batch.commit)
            logger.info(f"Successfully updated {count} documents with analysis_id: {analysis_id}")
        else:
            raise NotFoundException("Invalid document_ids provided")
        return documents
    
    async def create_analysis_session(self, payload: AnalysisRequest, user_id: Optional[str] = None) -> tuple[str, List[str]]:
        """Create a new analysis session and return analysis_id and storage_paths"""
        analysis_id = f"analysis_{uuid.uuid4().hex}"
        
        if payload.document_ids:
            storage_paths = await self.map_document_id_to_analysis_id(payload.document_ids, analysis_id)
        else:
            storage_paths = payload.storage_paths
        
        # Store initial session
        analysis_user_mapping_doc = {
            'analysis_id': analysis_id,
            'user_id': user_id,
            'is_active': True,
            'storage_paths': storage_paths,
            'document_ids': payload.document_ids,
            'created_at': datetime.now(),
        }

        firestore_client = get_firestore_client()
        doc_ref = firestore_client.collection(Collections.USER_ANALYSIS_MAPPING).document(analysis_id)
        await asyncio.to_thread(doc_ref.set, analysis_user_mapping_doc)

        analysis_doc = {
            'id': analysis_id,
            'user_id': user_id,
            'status': 'processing',
            'company_name': payload.company_name or 'Unknown',
            'storage_paths': storage_paths,
            'document_ids': payload.document_ids,
            'weighting_config': payload.weighting_config.model_dump() if payload.weighting_config else None,
            'created_at': datetime.now(),
            'progress': 0,
            'progress_message': 'Analysis initiated',
            'error': None
        }

        await db_insert(analysis_id, Collections.ANALYSIS, analysis_doc)
        
        return analysis_id, storage_paths
    
    async def process_analysis_safe(self, analysis_id: str, request: AnalysisRequest, storage_paths: List[str]):
        """Safe wrapper for analysis processing with comprehensive error handling"""
        try:
            await self.process_analysis(analysis_id, request, storage_paths)
        except Exception as e:
            logger.error(f"Critical error in background analysis {analysis_id}: {e}")
            try:
                error_update = {
                    'status': 'failed',
                    'error': f"Critical processing error: {str(e)}",
                    'failed_at': datetime.now(),
                    'progress_message': f'Analysis failed: {str(e)}'
                }
                await db_update(analysis_id, Collections.ANALYSIS, error_update)
            except Exception as update_error:
                logger.critical(f"Failed to record critical error for {analysis_id}: {update_error}")
    
    async def process_analysis(self, analysis_id: str, request: AnalysisRequest, storage_paths: List[str]):
        """Background task for analysis processing with improved error handling"""
        try:
            # Step 1: Document Processing
            await update_progress(analysis_id, 30, "Processing documents...")
            
            try:
                processed_data = await self.doc_processor.process_documents_from_storage(storage_paths)
            except Exception as e:
                raise ValueError(f"Document processing failed: {str(e)}")
            
            if not processed_data:
                raise ValueError("Document processing failed - no synthesized data extracted")

            if 'error' in processed_data:
                logger.error(f"Document processing error: {processed_data['error']}")
                raise ValueError(f"Document processing failed: {processed_data['error']}")
            
            # Validate processed data
            if not processed_data or 'synthesized_data' not in processed_data:
                raise ValueError("Document processing failed - no synthesized data extracted")
                
            await update_progress(analysis_id, 55, "Documents processed. Analyzing risk and benchmarking...", processed_data=processed_data)
            
            synthesized_data = processed_data['synthesized_data']

            # Running parallel tasks for risk analysis and benchmarking
            sector = synthesized_data.get('sector', 'unknown')
            tasks = [
                self.risk_analyzer.analyze_risks(analysis_id, synthesized_data), 
                self.benchmark_engine.calculate_percentiles(analysis_id, synthesized_data, sector)
            ]
            risk_results, benchmark_results = await asyncio.gather(*tasks, return_exceptions=True)
            for task_result in [risk_results, benchmark_results]:
                if isinstance(task_result, Exception):
                    raise ValueError(f"Analysis failed: {task_result}")
            
            await update_progress(analysis_id, 80, "Calculating scores...")
            weighting_config = request.weighting_config.model_dump() if request.weighting_config else {}
            try:
                weighted_scores = await self.weighting_calc.calculate_weighted_score(
                    analysis_id,
                    synthesized_data,
                    risk_results,
                    benchmark_results,
                    weighting_config
                )
            except Exception as e:
                raise ValueError(f"Score calculation failed: {str(e)}")
                        
            await update_progress(analysis_id, 90, "Generating deal note...")
            try:
                deal_note = await self.deal_generator.generate_deal_note(
                    analysis_id,
                    synthesized_data,
                    risk_results,
                    benchmark_results,
                    weighted_scores
                )
            except Exception as e:
                logger.warning(f"Deal note generation failed for {analysis_id}: {e}")
                deal_note = {"error": "Deal note generation failed", "details": str(e)}
                        
            # Store final results
            final_results = {
                'status': 'completed',
                'completed_at': datetime.now(),
                'progress': 100,
                'message': 'Analysis completed successfully',
                'error': None
            }
            await db_update(analysis_id, Collections.ANALYSIS, final_results)
            logger.info(f"Analysis {analysis_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {e}")
            error_update = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now(),
                'progress_message': f'Analysis failed: {str(e)}'
            }
            
            try:
                await db_update(analysis_id, Collections.ANALYSIS, error_update)
            except Exception as update_error:
                logger.critical(f"Failed to update error status for {analysis_id}: {update_error}")

    async def fetch_analysis_data(self, analysis_id: str) -> dict:
        """Fetch complete analysis data including all related collections"""
        data = await db_get(Collections.ANALYSIS, analysis_id)
        if not data:
            raise NotFoundException("Analysis not found")
        
        try:
            collection_key_mapping = {
                Collections.BENCHMARK_ANALYSIS: "benchmarking",
                Collections.RISK_ANALYSIS: "risk_assessment",
                Collections.DEAL_NOTE: "deal_note",
                Collections.WEIGHTED_SCORES: "weighted_scores"
            }
            map_name_tasks = {}
            for collection_name, key_name in collection_key_mapping.items():
                map_name_tasks[key_name] = db_get(collection_name, analysis_id)
            map_name_values = await asyncio_gather_dict(map_name_tasks)
            for map_name_key, result in map_name_values.items():
                data[map_name_key] = result

            data = self.serialize_datetime_fields(data)
            return sanitize_for_frontend(data)
            
        except Exception as e:
            logger.error(f"Failed to retrieve analysis {analysis_id}: {e}")
            raise ServerException(f"Failed to retrieve analysis: {str(e)}")

    async def update_weighting(self, analysis_id: str, weighting_config: dict) -> dict:
        """Recalculate scores with new weightings"""
        if not analysis_id or not analysis_id.startswith('analysis_'):
            raise ValueError("Invalid analysis ID format")
        
        if not weighting_config or not isinstance(weighting_config, dict):
            raise ValueError("Valid weighting configuration is required")
        
        firestore_client = get_firestore_client()
        doc = await asyncio.to_thread(
            lambda: firestore_client.collection(Collections.ANALYSIS).document(analysis_id).get()
        )
        
        if not doc.exists:
            raise NotFoundException("Analysis not found")
        
        analysis_data = doc.to_dict()
        current_status = analysis_data.get('status', 'unknown')
        if current_status != 'completed':
            raise ValueError(f"Analysis not completed yet. Current status: {current_status}")
        
        # Validate required data exists
        required_keys = ['processed_data', 'risk_assessment', 'benchmarking']
        missing_keys = [key for key in required_keys if key not in analysis_data]
        if missing_keys:
            raise ValueError(f"Analysis data incomplete. Missing: {', '.join(missing_keys)}")
        
        try:
            synthesized_data = analysis_data['processed_data']['synthesized_data']
        except (KeyError, TypeError):
            raise ValueError("Processed data structure is invalid")
        
        # Recalculate with new weights
        try:
            new_scores = await self.weighting_calc.calculate_weighted_score(
                analysis_id,
                synthesized_data,
                analysis_data['risk_assessment'],
                analysis_data['benchmarking'],
                weighting_config
            )
        except Exception as e:
            logger.error(f"Reweighting failed for {analysis_id}: {e}")
            raise ValueError("Failed to recalculate scores with new weights")
        
        # Update stored results
        update_data = {
            'weighted_scores': new_scores,
            'weighting_config': weighting_config,
            'updated_at': datetime.now()
        }
        await db_update(analysis_id, Collections.ANALYSIS, update_data)
        logger.info(f"Weighting updated successfully for {analysis_id}")
        
        return {
            "message": "Weighting updated successfully",
            "analysis_id": analysis_id,
            "new_scores": new_scores
        }

    async def get_bulk_analysis(self, user_id: str) -> dict:
        """Get bulk analysis data for a user"""
        try:
            data = await match_user_and_analysis_id(user_id)
        except Exception as error:
            logger.error(f"Error occurred while fetching analysis data: {error}")
            raise ServerException("Failed to fetch analysis data")
        
        return {
            "data": data,
            "message": "success"
        }

    async def delete_analysis(self, analysis_id: str, user_id: str) -> dict:
        """Delete an analysis by marking it as inactive"""
        try:
            data = await match_user_and_analysis_id(user_id, analysis_id)
        except Exception as error:
            logger.error(f"Error occurred while fetching analysis data: {error}")
            raise ServerException("Failed to verify analysis ownership")
        
        if not data:
            raise NotFoundException("Requested analysis does not exist")
        
        try:
            await db_update(analysis_id, Collections.USER_ANALYSIS_MAPPING, {"is_active": False})
        except Exception as error:
            logger.error(f"Exception while deleting analysis: {analysis_id}: error: {error}")
            raise ServerException("Failed to delete analysis")
        
        return {"data": "Analysis deleted successfully.", "message": True}

    @staticmethod
    def serialize_datetime_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively convert datetime objects to ISO strings"""
        if isinstance(data, dict):
            return {
                key: AnalysisService.serialize_datetime_fields(value) 
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [AnalysisService.serialize_datetime_fields(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data