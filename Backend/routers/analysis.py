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
        await update_progress(analysis_id, 10, "Processing documents...")
        
        try:
            processed_data = await doc_processor.process_documents_from_storage(request.storage_paths)
        except Exception as e:
            raise ValueError(f"Document processing failed: {str(e)}")
        if 'error' in processed_data:
            logger.error(f"Document processing error: {processed_data['error']}")
            raise ValueError(f"Document processing failed: {processed_data['error']}")
            
        await update_progress(analysis_id, 30, "Documents processed")

        # Validate processed data
        if not processed_data or 'synthesized_data' not in processed_data:
            raise ValueError("Document processing failed - no synthesized data extracted")
        
        synthesized_data = processed_data['synthesized_data']
        
        # Step 2: Risk Analysis
        await update_progress(analysis_id, 40, "Analyzing risks...")
        try:
            # TODO: Remove comments
            await asyncio.sleep(5)
            risk_results = {'risk_scores': {'financial': [], 'market': [{'type': 'unclear_target_market', 'severity': 5, 'details': 'Target market definition is unclear or too broad', 'impact': 'medium'}], 'team': [], 'product': [{'type': 'unclear_differentiation', 'severity': 6, 'details': 'Product differentiation is unclear or poorly defined', 'impact': 'medium'}], 'operational': [{'type': 'inconsistent_metrics', 'severity': 7, 'details': "The company's reported growth rate (0.43 or 43%) is identical to the stated market growth rate (0.43). This is highly unusual for a seed-stage company and suggests either a lack of specific company performance data or an aspirational target rather than actual organic growth, which can undermine data credibility.", 'impact': 'high'}, {'type': 'inconsistent_metrics', 'severity': 6, 'details': 'A long and impressive list of major corporate partnerships (e.g., Microsoft, Pfizer, Bosch, Saudi Telecom) is presented alongside only 5 customers. This raises questions about the effectiveness of these partnerships in converting to revenue-generating clients, their true depth, or the efficiency of the sales funnel.', 'impact': 'medium'}, {'type': 'unrealistic_claims', 'severity': 8, 'details': "Claiming a Client Lifetime Value (LTV) of '>$1,000,000', an LTV:CAC ratio of 'Minimum 10', and a 'Minimum 30% Profit After Tax (PAT)' with only 5 customers is highly ambitious and lacks sufficient data validation. These are likely aspirational projections rather than proven metrics, which could mislead stakeholders and pose significant risk if not achieved.", 'impact': 'critical'}, {'type': 'missing_info', 'severity': 7, 'details': "Critical operational information such as the total team size and specific key personnel roles (beyond the founders) is missing. This hinders a comprehensive assessment of the company's capacity, operational efficiency, and ability to scale, especially for an AI startup targeting large enterprises.", 'impact': 'high'}, {'type': 'unusual_pattern', 'severity': 6, 'details': "A monthly burn rate of $16,867 seems extremely low for an 'Agentic AI' company targeting 'medium to large enterprises' and claiming to provide a 'full data team experience'. While capital efficient, this suggests a very lean operation which might challenge the ability to provide enterprise-grade sales, support, and continuous development required by large clients.", 'impact': 'high'}, {'type': 'inconsistent_metrics', 'severity': 5, 'details': "The reported 'Booked Revenue' ($400,000 USD) is exactly the same as the 'Sales Pipeline Value' ($400,000 USD). This exact match is highly unusual and raises questions about how these metrics are defined and tracked, potentially indicating a lack of clear distinction between secured revenue and prospective deals.", 'impact': 'medium'}, {'type': 'missing_info', 'severity': 5, 'details': "The timeframe for the reported $400,000 revenue and 43% growth rate is not specified (e.g., annual, quarterly, or since inception). This ambiguity makes it difficult to accurately assess the company's current performance trajectory and financial health.", 'impact': 'medium'}, {'type': 'unrealistic_claims', 'severity': 6, 'details': "The product is described as being in 'Early product deployment / early traction' but 'established product' and 'low R&D costs' are listed as competitive advantages. These statements can be contradictory, suggesting an overstatement of product maturity or an underestimation of ongoing R&D needs in a rapidly evolving AI sector.", 'impact': 'medium'}, {'type': 'missing_info', 'severity': 4, 'details': "Valuation is listed as 'null'. For a seed-stage company with stated revenue and funding raised, an approximate pre-money or post-money valuation associated with the last funding round would typically be available, indicating a gap in financial transparency.", 'impact': 'low'}]}, 'overall_risk_score': 5.5, 'risk_explanations': ["**Operational Risk**: Claiming a Client Lifetime Value (LTV) of '>$1,000,000', an LTV:CAC ratio of 'Minimum 10', and a 'Minimum 30% Profit After Tax (PAT)' with only 5 customers is highly ambitious and lacks sufficient data validation. These are likely aspirational projections rather than proven metrics, which could mislead stakeholders and pose significant risk if not achieved. (Impact: critical)", "**Operational Risk**: The company's reported growth rate (0.43 or 43%) is identical to the stated market growth rate (0.43). This is highly unusual for a seed-stage company and suggests either a lack of specific company performance data or an aspirational target rather than actual organic growth, which can undermine data credibility. (Impact: high)", "**Operational Risk**: Critical operational information such as the total team size and specific key personnel roles (beyond the founders) is missing. This hinders a comprehensive assessment of the company's capacity, operational efficiency, and ability to scale, especially for an AI startup targeting large enterprises. (Impact: high)", '**Overall Assessment**: 3 high-severity risks identified across 5 categories.'], 'risk_summary': {'total_risks': 11, 'by_severity': {'low': 0, 'medium': 8, 'high': 3, 'critical': 0}, 'by_category': {'financial': 0, 'market': 1, 'team': 0, 'product': 1, 'operational': 9}, 'average_severity': 5.91}, 'analysis_metadata': {'categories_analyzed': 5, 'total_risks_identified': 11, 'high_severity_risks': 3}}
            # risk_results = await risk_analyzer.analyze_risks(synthesized_data)
        except Exception as e:
            raise ValueError(f"Risk analysis failed: {str(e)}")
            
        await update_progress(analysis_id, 55, "Risk assessment complete")
        
        # Step 3: Benchmarking
        await update_progress(analysis_id, 60, "Running benchmarks...")
        sector = synthesized_data.get('sector', 'unknown')
        try:
            # TODO: remove comments
            await asyncio.sleep(5)
            benchmark_results = {'percentiles': {'growth_rate': {'value': 0.43, 'percentile': 5, 'interpretation': 'Poor - Bottom 20% performance', 'benchmark_median': 280.0, 'benchmark_top_quartile': 450.0, 'relative_performance': 'Below median'}, 'burn_rate': {'value': 16867.0, 'percentile': 95, 'interpretation': 'Excellent - Top 20% performance', 'benchmark_median': 85000.0, 'benchmark_top_quartile': 130000.0, 'relative_performance': 'Significantly better than median'}, 'runway': {'value': 6.0, 'percentile': 5, 'interpretation': 'Poor - Bottom 20% performance', 'benchmark_median': 19, 'benchmark_top_quartile': 23, 'relative_performance': 'Below median'}, 'revenue': {'value': 400000.0, 'percentile': 95, 'interpretation': 'Excellent - Top 20% performance', 'benchmark_median': 14.0, 'benchmark_top_quartile': 20.0, 'relative_performance': 'Significantly above median'}}, 'overall_score': {'score': 43.6, 'grade': 'D', 'metrics_count': 4}, 'sector_benchmarks': {'revenue_multiples': {'p10': 6.0, 'p25': 9.0, 'p50': 14.0, 'p75': 20.0, 'p90': 28.0}, 'growth_rates': {'p10': 90.0, 'p25': 160.0, 'p50': 280.0, 'p75': 450.0, 'p90': 750.0}, 'team_sizes': {'p10': 5, 'p25': 8, 'p50': 13, 'p75': 19, 'p90': 26}, 'burn_rates_monthly': {'p10': 30000.0, 'p25': 50000.0, 'p50': 85000.0, 'p75': 130000.0, 'p90': 200000.0}, 'runway_months': {'p10': 13, 'p25': 16, 'p50': 19, 'p75': 23, 'p90': 27}, 'valuation_millions': {'p10': 6.0, 'p25': 9.5, 'p50': 14.0, 'p75': 20.0, 'p90': 28.0}}, 'insights': ['While achieving strong early revenue (75th+ percentile) demonstrates solid product-market fit, the significantly lower growth rate (below 40th percentile) indicates a critical bottleneck in scaling. Prioritize identifying and investing in scalable growth channels – be it sales, marketing, or product-led growth – to accelerate customer acquisition and leverage existing market validation.', 'The combination of a healthy burn rate (75th+ percentile) and strong revenue is positive, but the short runway (below 40th percentile) alongside weak growth creates an urgent funding need. Leverage the strong revenue and efficient operations to aggressively pursue a follow-on funding round, while simultaneously mapping out a contingency plan to extend runway without further sacrificing growth potential.', 'In the competitive AI/Data Analytics sector, slow growth risks falling behind despite current revenue strength. Re-evaluate if the efficient burn rate (75th+ percentile) is inadvertently hindering investment in growth-critical areas like R&D, talent acquisition, or market expansion. Strategically allocate more capital towards these areas to boost growth, even if it moderately increases burn, to secure future market position and investor confidence.'], 'analysis_date': '2025-09-19T01:06:35.008483', 'data_source': 'gemini_ai'}
            # benchmark_results = await benchmark_engine.calculate_percentiles(
            #     synthesized_data, 
            #     sector
            # )
        except Exception as e:
            raise ValueError(f"Benchmarking failed: {str(e)}")
            
        await update_progress(analysis_id, 75, "Benchmarking complete")
        
        # Step 4: Weighted Scoring
        await update_progress(analysis_id, 80, "Calculating scores...")
        weighting_config = request.weighting_config.model_dump() if request.weighting_config else {}
        try:
            weighted_scores = await weighting_calc.calculate_weighted_score(
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


async def update_progress(analysis_id: str, progress: int, message: str):
    """Update analysis progress"""
    try:
        update_data = {
            'progress': progress,
            'progress_message': message,
            'updated_at': datetime.now()
        }
        firestore_client = get_firestore_client()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: firestore_client.collection('analyses').document(analysis_id).update(update_data)
        )
    except Exception as e:
        print(f"Failed to update progress for {analysis_id}: {e}")

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
        
        return data
        
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