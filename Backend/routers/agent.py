# routers/agent.py
from fastapi import APIRouter, HTTPException
from google import genai
from google.genai import types
from typing import List, Dict, Any
import json
import logging
import asyncio

from models.schemas import ChatRequest, ChatResponse
from models.database import get_firestore_client
from utils.ai_client import monitor_usage, configure_gemini
from settings import PROJECT_ID, GCP_REGION

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)

# Question categories for better follow-up generation
QUESTION_CATEGORIES = {
    'financial': ['revenue', 'profit', 'cash', 'funding', 'valuation', 'burn', 'runway'],
    'risk': ['risk', 'threat', 'challenge', 'problem', 'concern', 'issue'],
    'market': ['market', 'competition', 'competitor', 'industry', 'sector', 'tam', 'demand'],
    'team': ['team', 'founder', 'management', 'leadership', 'experience', 'background'],
    'growth': ['growth', 'scale', 'expansion', 'potential', 'future', 'forecast'],
    'product': ['product', 'technology', 'innovation', 'differentiation', 'advantage']
}

@router.post("/chat", response_model=ChatResponse)
@monitor_usage("gemini_requests")
async def agent_chat(request: ChatRequest):
    """Handle agent conversations with comprehensive analysis context"""
    
    try:
        # Enhanced input validation
        if not request.analysis_id or not request.analysis_id.strip():
            raise HTTPException(status_code=400, detail="Analysis ID is required")
        
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="Question is required")
        
        if len(request.question.strip()) > 1000:
            raise HTTPException(status_code=400, detail="Question too long (max 1000 characters)")
        
        # Get analysis context asynchronously
        analysis_data = await get_analysis_data(request.analysis_id.strip())
        
        # Build enhanced context prompt
        context_prompt = await build_context_prompt(analysis_data)
        
        # Generate AI response
        ai_response = await generate_ai_response(context_prompt, request.question.strip())
        
        # Generate contextual follow-up suggestions
        suggestions = await generate_follow_up_questions(analysis_data, request.question.strip())

        return ChatResponse(
            response=ai_response,
            suggested_questions=suggestions,
            analysis_id=request.analysis_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in agent_chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")

async def get_analysis_data(analysis_id: str) -> Dict[str, Any]:
    """Retrieve and validate analysis data"""
    
    try:
        firestore_client = get_firestore_client()
        
        # Use async executor for Firestore operation
        analysis_doc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: firestore_client.collection('analyses').document(analysis_id).get()
        )
        
        if not analysis_doc.exists:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis_data = analysis_doc.to_dict()
        if not analysis_data:
            raise HTTPException(status_code=404, detail="Analysis data is empty")
            
        if analysis_data.get('status') != 'completed':
            current_status = analysis_data.get('status', 'unknown')
            raise HTTPException(
                status_code=400, 
                detail=f"Analysis not ready for chat. Current status: {current_status}"
            )
        
        return analysis_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis data")

async def build_context_prompt(analysis_data: Dict[str, Any]) -> str:
    """Build comprehensive context prompt for AI"""
    
    try:
        # Safely extract data with defaults
        company_name = analysis_data.get('company_name', 'Unknown Company')
        processed_data = analysis_data.get('processed_data', {})
        synthesized_data = processed_data.get('synthesized_data', {})
        
        # Extract key metrics
        sector = synthesized_data.get('sector', 'Unknown Sector')
        risk_assessment = analysis_data.get('risk_assessment', {})
        risk_score = risk_assessment.get('overall_risk_score')
        weighted_scores = analysis_data.get('weighted_scores', {})
        overall_score = weighted_scores.get('overall_score')
        
        # Format recommendation safely
        recommendation = weighted_scores.get('recommendation', {})
        if isinstance(recommendation, dict):
            tier = recommendation.get('tier', 'N/A')
            rationale = recommendation.get('rationale', 'No rationale provided')
        else:
            tier = str(recommendation) if recommendation else 'N/A'
            rationale = 'No detailed rationale available'
        
        # Extract benchmarking data
        benchmarking = analysis_data.get('benchmarking', {})
        benchmark_info = ""
        if benchmarking:
            percentiles = benchmarking.get('percentiles', {})
            if percentiles:
                benchmark_info = f"\nBenchmark Percentiles: {json.dumps(percentiles, indent=2)}"
        
        # Extract key risks
        risks_info = ""
        if risk_assessment:
            risks = risk_assessment.get('identified_risks', [])
            if risks:
                top_risks = risks[:3] if isinstance(risks, list) else []
                risks_info = f"\nTop Risks: {json.dumps(top_risks, indent=2)}"
        
        # Build comprehensive context
        context_prompt = f"""
            You are an expert startup investment analyst with access to comprehensive analysis data.

            COMPANY OVERVIEW:
            Company: {company_name}
            Sector: {sector}

            ANALYSIS SCORES:
            - Overall Investment Score: {f"{overall_score:.1f}/10" if overall_score is not None else "N/A"}
            - Risk Score: {f"{risk_score:.1f}/10" if risk_score is not None else "N/A"}
            - Investment Tier: {tier}
            - Rationale: {rationale}

            KEY FINANCIAL & BUSINESS METRICS:
            {json.dumps(synthesized_data, indent=2)[:1500] if synthesized_data else "Limited data available"}
            {benchmark_info}
            {risks_info}

            INSTRUCTIONS:
            1. Answer questions with specific reference to the analysis data above
            2. Be concise, actionable, and professional
            3. Provide quantitative insights where possible
            4. Reference specific data points from the analysis
            5. If data is missing, acknowledge limitations clearly
            6. Focus on investment-relevant insights
        """
        
        return context_prompt
        
    except Exception as e:
        logger.error(f"Error building context prompt: {str(e)}")
        return f"Limited context available for {analysis_data.get('company_name', 'this company')}."

async def generate_ai_response(context_prompt: str, question: str) -> str:
    """Generate AI response with proper error handling"""
    
    try:
        # Use async executor for AI generation
        def _generate_response():
            configure_gemini()
            model = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=GCP_REGION
            )
            
            full_prompt = f"{context_prompt}\n\nINVESTOR QUESTION: {question}\n\nANSWER:"
            
            generation_config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1000,
                top_p=0.8,
                top_k=40,
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                ]
            )
            
            response = model.models.generate_content(
                model="gemini-2.5-flash",
                contents = [full_prompt],
                config=generation_config
            )
            
            return response.text
        
        response_text = await asyncio.get_event_loop().run_in_executor(None, _generate_response)
        
        if not response_text or not response_text.strip():
            raise HTTPException(status_code=500, detail="AI model returned empty response")
            
        return response_text.strip()
        
    except Exception as e:
        logger.error(f"AI generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response")

def categorize_question(question: str) -> str:
    """Categorize question to generate relevant follow-ups"""
    
    question_lower = question.lower()
    
    for category, keywords in QUESTION_CATEGORIES.items():
        if any(keyword in question_lower for keyword in keywords):
            return category
    
    return 'general'

async def generate_follow_up_questions(analysis_data: Dict[str, Any], current_question: str) -> List[str]:
    """Generate contextual follow-up questions based on analysis data and current question"""
    
    try:
        suggestions = []
        question_category = categorize_question(current_question)
        
        # Safely extract scores
        risk_score = safe_float_convert(
            analysis_data.get('risk_assessment', {}).get('overall_risk_score', 0)
        )
        overall_score = safe_float_convert(
            analysis_data.get('weighted_scores', {}).get('overall_score', 0)
        )
        
        # Get company info
        company_name = analysis_data.get('company_name', 'this company')
        sector = analysis_data.get('processed_data', {}).get('synthesized_data', {}).get('sector', '')
        
        # Generate category-specific follow-ups based on current question
        if question_category == 'financial':
            suggestions.extend([
                f"What are the key financial risks for {company_name}?",
                "How does the burn rate compare to industry benchmarks?",
                "What's the path to profitability timeline?"
            ])
        elif question_category == 'risk':
            suggestions.extend([
                "What mitigation strategies exist for the top risks?",
                f"How do these risks compare to other {sector} companies?" if sector else "How do these risks compare to industry standards?",
                "What would trigger a significant increase in risk level?"
            ])
        elif question_category == 'market':
            suggestions.extend([
                f"What's {company_name}'s competitive advantage?",
                "How large is the addressable market opportunity?",
                "What market trends could impact this investment?"
            ])
        elif question_category == 'team':
            suggestions.extend([
                "What are the key team strengths and gaps?",
                "How does leadership experience align with company needs?",
                "What advisory support does the team have?"
            ])
        elif question_category == 'growth':
            suggestions.extend([
                "What are the primary growth drivers?",
                "What could accelerate or hinder scale potential?",
                "How scalable is the business model?"
            ])
        elif question_category == 'product':
            suggestions.extend([
                "What's the product-market fit evidence?",
                "How defensible is the technology/product?",
                "What's the product development roadmap?"
            ])
        
        # Add score-based contextual suggestions
        if risk_score > 7:
            suggestions.append("What specific steps could mitigate the highest risks?")
        elif risk_score < 4:
            suggestions.append("Are there any hidden risks we should consider?")
        
        if overall_score > 8:
            suggestions.append("What could cause this strong opportunity to fail?")
        elif overall_score < 5:
            suggestions.append("What needs to change to make this investment attractive?")
        
        # Add sector-specific suggestions
        if sector and sector != 'Unknown Sector':
            suggestions.append(f"How does this compare to other {sector} investments?")
        
        # Remove duplicates and avoid similar questions to current
        unique_suggestions = []
        current_words = set(current_question.lower().split())
        
        for suggestion in suggestions:
            suggestion_words = set(suggestion.lower().split())
            # Avoid suggestions too similar to current question
            if len(current_words.intersection(suggestion_words)) < len(current_words) * 0.6:
                if suggestion not in unique_suggestions:
                    unique_suggestions.append(suggestion)
        
        # Ensure we have some suggestions even if filtering removed them all
        if not unique_suggestions:
            unique_suggestions = [
                "What are the main investment highlights?",
                "What factors could impact the success of this investment?",
                "How does this opportunity fit in a diversified portfolio?"
            ]
        
        return unique_suggestions[:4]
        
    except Exception as e:
        logger.warning(f"Error generating follow-up questions: {str(e)}")
        return [
            "What are the key investment considerations?",
            "How does this compare to similar opportunities?",
            "What additional information would be helpful?"
        ]

def safe_float_convert(value: Any) -> float:
    """Safely convert value to float with fallback"""
    
    if value is None:
        return 0.0
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
