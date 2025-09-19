# services/deal_generator.py
from google import genai
from google.genai import types

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import os
from dataclasses import dataclass
import asyncio
from functools import wraps
from utils.ai_client import configure_gemini

logger = logging.getLogger(__name__)

@dataclass
class DealNoteConfig:
    """Configuration for deal note generation"""
    max_prompt_length: int = 4000
    max_retries: int = 3
    timeout_seconds: int = 30
    model_name: str = 'gemini-pro'
    temperature: float = 0.7

def async_timeout(seconds: int):
    """Decorator to add timeout to async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {seconds} seconds")
                raise TimeoutError(f"Operation timed out after {seconds} seconds")
        return wrapper
    return decorator

class DealNoteGenerator:
    def __init__(self, config: Optional[DealNoteConfig] = None):
        self.config = config or DealNoteConfig()
        self._model = None
        self._initialize_genai()
    
    def _initialize_genai(self):
        """Initialize Google Generative AI with proper error handling"""
        try:
            configure_gemini()
            self._model = genai.Client(
                vertexai=True,
                project="ventureval-ef705",
                location="us-central1"
            )
            
            # self._model = genai.GenerativeModel(
            #     self.config.model_name,
            #     generation_config=genai.types.GenerationConfig(
            #         temperature=self.config.temperature,
            #         max_output_tokens=2048,
            #         candidate_count=1
            #     )
            # )
            logger.info("Google Generative AI initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Generative AI: {e}")
            self._model = None
    
    @async_timeout(30)
    async def generate_deal_note(
        self, 
        startup_data: Dict[str, Any], 
        risk_assessment: Dict[str, Any], 
        benchmark_results: Dict[str, Any], 
        weighted_scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive deal note with robust error handling"""
        
        # Validate inputs
        if not self._validate_inputs(startup_data, risk_assessment, benchmark_results, weighted_scores):
            return self._create_error_response("Invalid input data provided")
        
        # Check if AI model is available
        if not self._model:
            logger.warning("AI model not available, generating fallback summary")
            return self._create_fallback_response(startup_data, weighted_scores, "AI model not initialized")
        
        try:
            # Generate the deal note with retries
            content = await self._generate_with_retries(
                startup_data, risk_assessment, benchmark_results, weighted_scores
            )
            
            return self._create_success_response(
                startup_data, weighted_scores, risk_assessment, content
            )
            
        except Exception as e:
            logger.error(f"Deal note generation failed: {e}")
            return self._create_fallback_response(startup_data, weighted_scores, str(e))
    
    def _validate_inputs(self, startup_data: Dict, risk_assessment: Dict, 
                        benchmark_results: Dict, weighted_scores: Dict) -> bool:
        """Validate input data"""
        try:
            # Check if all inputs are dictionaries
            inputs = [startup_data, risk_assessment, benchmark_results, weighted_scores]
            if not all(isinstance(inp, dict) for inp in inputs):
                logger.error("One or more inputs are not dictionaries")
                return False
            
            # Check for essential fields
            if not startup_data.get('company_name'):
                logger.warning("Company name not provided in startup_data")
            
            # Validate numeric scores
            risk_score = risk_assessment.get('overall_risk_score')
            if risk_score is not None and not isinstance(risk_score, (int, float)):
                logger.warning("Invalid risk score format")
            
            overall_score = weighted_scores.get('overall_score')
            if overall_score is not None and not isinstance(overall_score, (int, float)):
                logger.warning("Invalid overall score format")
            
            return True
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            return False
    
    async def _generate_with_retries(
        self, 
        startup_data: Dict, 
        risk_assessment: Dict, 
        benchmark_results: Dict, 
        weighted_scores: Dict
    ) -> str:
        """Generate content with retry logic"""
        
        for attempt in range(self.config.max_retries):
            try:
                prompt = self._build_prompt(startup_data, risk_assessment, benchmark_results, weighted_scores)
                
                # Run the synchronous generation in an executor to make it truly async
                generation_config = types.GenerateContentConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=2048,
                    candidate_count=1
                )

                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self._model.models.generate_content(model="gemini-2.5-flash",contents = [prompt], config=generation_config)
                )
                
                if response and hasattr(response, 'text') and response.text:
                    return response.text.strip()
                else:
                    raise ValueError("Empty response from AI model")
                    
            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_retries - 1:
                    raise e
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("All generation attempts failed")
    
    def _build_prompt(
        self, 
        startup_data: Dict, 
        risk_assessment: Dict, 
        benchmark_results: Dict, 
        weighted_scores: Dict
    ) -> str:
        """Build a structured prompt with length limits"""
        
        # Safely extract data with defaults
        company_name = startup_data.get('company_name', 'Unknown Company')
        sector = startup_data.get('sector', 'Unknown')
        stage = startup_data.get('stage', 'Unknown')
        
        risk_score = risk_assessment.get('overall_risk_score', 0)
        risk_explanations = risk_assessment.get('risk_explanations', [])
        if isinstance(risk_explanations, list):
            risk_summary = '; '.join(str(risk) for risk in risk_explanations[:3])
        else:
            risk_summary = str(risk_explanations)[:200]
        
        overall_score = weighted_scores.get('overall_score', 0)
        recommendation_tier = weighted_scores.get('recommendation', {}).get('tier', 'N/A')
        
        # Safely serialize complex data with length limits
        startup_data_str = self._safe_json_dump(startup_data, 1500)
        benchmark_str = self._safe_json_dump(benchmark_results, 800)
        
        prompt = f"""
            Generate a professional investment deal note for {company_name} based on the analysis below.

            COMPANY OVERVIEW:
            - Name: {company_name}
            - Sector: {sector}
            - Stage: {stage}
            - Overall Score: {overall_score:.1f}/10
            - Recommendation: {recommendation_tier}

            STARTUP DATA (key metrics):
            {startup_data_str}

            RISK ASSESSMENT:
            - Overall Risk Score: {risk_score:.1f}/10
            - Key Risk Areas: {risk_summary}

            BENCHMARKING RESULTS:
            {benchmark_str}

            Please generate a structured deal note with these exact sections:

            **EXECUTIVE SUMMARY**
            3-4 sentences covering the investment opportunity, key strengths, and recommendation.

            **INVESTMENT THESIS**
            3 bullet points highlighting the main reasons to invest or pass.

            **KEY METRICS**
            Financial highlights and important business metrics.

            **MARKET OPPORTUNITY**
            Market size, growth potential, and competitive landscape.

            **TEAM ASSESSMENT**
            Founder and team evaluation.

            **PRODUCT/TECHNOLOGY**
            Product differentiation and development stage.

            **RISK FACTORS**
            Top 3 risks with brief mitigation strategies.

            **BENCHMARKING INSIGHTS**
            How this company compares to sector peers.

            **RECOMMENDATION**
            Clear Pass/Consider/Pursue decision with 2-3 sentence rationale.

            **NEXT STEPS**
            3-5 specific actionable items for further due diligence.

            Keep the total response under 1500 words. Be concise but comprehensive.
        """
        
        # Ensure prompt doesn't exceed length limit
        if len(prompt) > self.config.max_prompt_length:
            prompt = prompt[:self.config.max_prompt_length] + "\n\n[Content truncated due to length limits]"
        
        return prompt
    
    def _safe_json_dump(self, data: Any, max_length: int) -> str:
        """Safely serialize data to JSON with length limits"""
        try:
            json_str = json.dumps(data, indent=2, default=str)
            if len(json_str) > max_length:
                # Truncate and try to keep it valid
                truncated = json_str[:max_length]
                # Find the last complete line
                last_newline = truncated.rfind('\n')
                if last_newline > 0:
                    truncated = truncated[:last_newline]
                return truncated + "\n  [... data truncated ...]"
            return json_str
        except Exception as e:
            logger.warning(f"JSON serialization failed: {e}")
            return f"[Unable to serialize data: {str(data)[:200]}...]"
    
    def _create_success_response(
        self, 
        startup_data: Dict, 
        weighted_scores: Dict, 
        risk_assessment: Dict, 
        content: str
    ) -> Dict[str, Any]:
        """Create successful response structure"""
        
        financials = startup_data.get('financials', {})
        
        return {
            'generated_at': datetime.now().isoformat(),
            'company_name': startup_data.get('company_name', 'Unknown Company'),
            'analyst_recommendation': weighted_scores.get('recommendation', {}).get('tier', 'N/A'),
            'overall_score': weighted_scores.get('overall_score', 0),
            'content': content,
            'content_type': 'ai_generated',
            'word_count': len(content.split()) if content else 0,
            'summary_stats': {
                'risk_score': risk_assessment.get('overall_risk_score', 0),
                'sector': startup_data.get('sector', 'Unknown'),
                'stage': startup_data.get('stage', 'Unknown'),
                'revenue': financials.get('revenue') if isinstance(financials, dict) else None,
                'growth_rate': financials.get('growth_rate') if isinstance(financials, dict) else None,
                'team_size': startup_data.get('team_size'),
                'funding_raised': startup_data.get('funding_raised')
            },
            'generation_metadata': {
                'model_used': self.config.model_name,
                'temperature': self.config.temperature,
                'generated_successfully': True
            }
        }
    
    def _create_fallback_response(
        self, 
        startup_data: Dict, 
        weighted_scores: Dict, 
        error_message: str
    ) -> Dict[str, Any]:
        """Create fallback response when AI generation fails"""
        
        fallback_content = self._generate_fallback_summary(startup_data, weighted_scores)
        
        return {
            'generated_at': datetime.now().isoformat(),
            'company_name': startup_data.get('company_name', 'Unknown Company'),
            'analyst_recommendation': weighted_scores.get('recommendation', {}).get('tier', 'N/A'),
            'overall_score': weighted_scores.get('overall_score', 0),
            'content': fallback_content,
            'content_type': 'fallback_summary',
            'error': f'AI generation failed: {error_message}',
            'word_count': len(fallback_content.split()),
            'summary_stats': {
                'sector': startup_data.get('sector', 'Unknown'),
                'stage': startup_data.get('stage', 'Unknown'),
                'revenue': startup_data.get('financials', {}).get('revenue') if isinstance(startup_data.get('financials'), dict) else None
            },
            'generation_metadata': {
                'model_used': 'fallback',
                'generated_successfully': False,
                'error': error_message
            }
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            'generated_at': datetime.now().isoformat(),
            'error': error_message,
            'content_type': 'error',
            'content': 'Deal note generation failed due to invalid inputs.',
            'generation_metadata': {
                'generated_successfully': False,
                'error': error_message
            }
        }
    
    def _generate_fallback_summary(self, startup_data: Dict, weighted_scores: Dict) -> str:
        """Generate enhanced fallback summary when AI generation fails"""
        
        company_name = startup_data.get('company_name', 'Unknown Company')
        sector = startup_data.get('sector', 'Unknown')
        stage = startup_data.get('stage', 'Unknown')
        
        recommendation_data = weighted_scores.get('recommendation', {})
        recommendation = recommendation_data.get('tier', 'N/A')
        reasoning = recommendation_data.get('reasoning', 'No reasoning available')
        
        score = weighted_scores.get('overall_score', 0)
        
        # Extract financial information safely
        financials = startup_data.get('financials', {})
        if isinstance(financials, dict):
            revenue = financials.get('revenue', 'Not disclosed')
            growth_rate = financials.get('growth_rate', 'Not disclosed')
        else:
            revenue = growth_rate = 'Not disclosed'
        
        team_size = startup_data.get('team_size', 'Not disclosed')
        funding_raised = startup_data.get('funding_raised', 'Not disclosed')
        
        return f"""
            **DEAL SUMMARY - {company_name}**

            **EXECUTIVE SUMMARY**
            {company_name} is a {sector} company in the {stage} stage. Based on our analysis, we recommend: {recommendation} (Score: {score:.1f}/10).

            **KEY INFORMATION**
            • Sector: {sector}
            • Stage: {stage}
            • Overall Score: {score:.1f}/10
            • Recommendation: {recommendation}
            • Team Size: {team_size}
            • Revenue: {revenue}
            • Growth Rate: {growth_rate}
            • Funding Raised: {funding_raised}

            **RECOMMENDATION RATIONALE**
            {reasoning}

            **NOTE**
            This is a basic summary generated when full AI analysis is unavailable. 
            For comprehensive insights, please review the detailed analysis data including:
            - Risk assessment details
            - Benchmarking results against sector peers
            - Individual scoring components
            - Market analysis data

            **NEXT STEPS**
            1. Review detailed risk assessment
            2. Compare benchmarking data with sector standards
            3. Analyze financial projections and assumptions
            4. Conduct team and market validation
            5. Schedule follow-up analysis when AI services are restored
        """