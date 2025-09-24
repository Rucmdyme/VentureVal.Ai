# services/deal_generator.py
from google import genai
from google.genai import types

import json
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
import os
from dataclasses import dataclass
import asyncio
from functools import wraps
from utils.ai_client import configure_gemini
from settings import PROJECT_ID, GCP_REGION
from utils.enhanced_text_cleaner import sanitize_for_frontend

logger = logging.getLogger(__name__)

@dataclass
class DealNoteConfig:
    """Configuration for deal note generation"""
    max_prompt_length: int = 12000
    max_retries: int = 3
    timeout_seconds: int = 60
    model_name: str = 'gemini-2.5-flash'
    temperature: float = 0.3

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

def format_large_number(value: Any) -> Any:
    """Format large numbers with appropriate units (B, M, K) for display"""
    if value is None:
        return None
    
    try:
        num_value = float(value)
        if num_value >= 1_000_000_000:
            return f"{num_value / 1_000_000_000:.1f}B"
        elif num_value >= 1_000_000:
            return f"{num_value / 1_000_000:.1f}M"
        elif num_value >= 1_000:
            return f"{num_value / 1_000:.0f}K"
        else:
            return num_value
    except (ValueError, TypeError):
        return value

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
                project=PROJECT_ID,
                location=GCP_REGION
            )
            
            logger.info("Google Generative AI initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Generative AI: {e}")
            self._model = None
    
    @async_timeout(60)
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
                startup_data, weighted_scores, risk_assessment, content, benchmark_results
            )
            
        except Exception as e:
            logger.error(f"Deal note generation failed: {e}")
            return self._create_fallback_response(startup_data, weighted_scores, str(e))
    

    def _calculate_years_in_operation(self, founded_value: Any) -> Optional[int]:
        """Safely calculate years in operation from founded year"""
        if founded_value is None:
            return None
        
        try:
            # Handle different types of founded values
            if isinstance(founded_value, (int, float)):
                founded_year = int(founded_value)
            elif isinstance(founded_value, str):
                # Try to extract year from string
                founded_year = int(founded_value.strip())
            else:
                return None
            
            # Validate year is reasonable
            current_year = datetime.now().year
            if 1900 <= founded_year <= current_year:
                return current_year - founded_year
            else:
                return None
                
        except (ValueError, TypeError):
            return None

    def _extract_numerical_stats(self, startup_data: Dict, risk_assessment: Dict, 
                                benchmark_results: Dict, weighted_scores: Dict) -> Dict[str, Any]:
        """Extract all numerical statistics from the data"""
        
        try:
            # Extract financial data
            financials = startup_data.get('financials', {})
            if not isinstance(financials, dict):
                financials = {}
            
            # Extract market data
            market = startup_data.get('market', {})
            if not isinstance(market, dict):
                market = {}
            
            # Extract team data
            team = startup_data.get('team', {})
            if not isinstance(team, dict):
                team = {}
            
            # Extract traction data
            traction = startup_data.get('traction', {})
            if not isinstance(traction, dict):
                traction = {}
            
            # Extract benchmark percentiles
            percentiles = benchmark_results.get('percentiles', {})
            if not isinstance(percentiles, dict):
                percentiles = {}
            
            # Build comprehensive numerical stats
            stats = {
                # Core scores
                'overall_score': weighted_scores.get('overall_score'),
                'risk_score': risk_assessment.get('overall_risk_score'),
                'benchmark_score': benchmark_results.get('overall_score', {}).get('score'),
                
                # Financial metrics
                'revenue': financials.get('revenue'),
                'monthly_revenue': financials.get('monthly_revenue'),
                'annual_revenue': financials.get('annual_revenue'),
                'growth_rate': financials.get('growth_rate'),
                'burn_rate': financials.get('burn_rate'),
                'monthly_burn': financials.get('monthly_burn'),
                'runway_months': financials.get('runway_months'),
                'funding_raised': financials.get('funding_raised') or startup_data.get('funding_raised'),
                'funding_seeking': financials.get('funding_seeking'),
                'valuation': financials.get('valuation'),
                'gross_margin': financials.get('gross_margin'),
                'net_margin': financials.get('net_margin'),
                'cac': financials.get('cac'),
                'ltv': financials.get('ltv'),
                'ltv_cac_ratio': financials.get('ltv_cac_ratio'),
                'payback_period': financials.get('payback_period'),
                'churn_rate': financials.get('churn_rate'),
                'mrr': financials.get('mrr'),
                'arr': financials.get('arr'),
                'revenue_projections': financials.get('revenue_projections'),
                
                # Market metrics
                'tam': market.get('size'),
                'sam': market.get('sam'),
                'som': market.get('som'),
                'market_growth_rate': market.get('growth_rate'),
                
                # Team metrics
                'team_size': team.get('size') or startup_data.get('team_size'),
                'engineering_team_size': team.get('engineering_size'),
                'sales_team_size': team.get('sales_size'),
                'founded_year': startup_data.get('founded'),
                'years_in_operation': self._calculate_years_in_operation(startup_data.get('founded')),
                
                # Traction metrics
                'customers': traction.get('customers'),
                'active_users': traction.get('active_users'),
                'monthly_active_users': traction.get('mau'),
                'daily_active_users': traction.get('dau'),
                'user_growth_rate': traction.get('user_growth_rate'),
                'customer_growth_rate': traction.get('customer_growth_rate'),
                'retention_rate': traction.get('retention_rate'),
                'nps_score': traction.get('nps_score'),
                
                # Benchmark percentiles
                'revenue_percentile': percentiles.get('revenue', {}).get('percentile'),
                'growth_rate_percentile': percentiles.get('growth_rate', {}).get('percentile'),
                'team_size_percentile': percentiles.get('team_size', {}).get('percentile'),
                'funding_percentile': percentiles.get('funding_raised', {}).get('percentile'),
                'burn_rate_percentile': percentiles.get('burn_rate', {}).get('percentile'),
                'runway_percentile': percentiles.get('runway_months', {}).get('percentile'),
                
                # Additional metrics from synthesized data if available
                'synthesized_revenue': startup_data.get('synthesized_data', {}).get('financials', {}).get('revenue'),
                'synthesized_growth_rate': startup_data.get('synthesized_data', {}).get('financials', {}).get('growth_rate'),
                'synthesized_team_size': startup_data.get('synthesized_data', {}).get('team', {}).get('size'),
                'synthesized_customers': startup_data.get('synthesized_data', {}).get('traction', {}).get('customers'),
            }
            
            # Define keys that should be formatted as large numbers (B, M, K)
            large_number_keys = {
                'revenue', 'monthly_revenue', 'annual_revenue', 'funding_raised', 'funding_seeking', 
                'valuation', 'mrr', 'arr', 'market_size', 'tam', 'sam', 'som', 'customers', 
                'active_users', 'monthly_active_users', 'daily_active_users', 'synthesized_revenue', 
                'synthesized_customers', 'cac', 'ltv'
            }
            
            # Filter out None values and keep only numerical data
            numerical_stats = {}
            for key, value in stats.items():
                try:
                    if value is not None and isinstance(value, (int, float)):
                        # Apply formatting for large numbers
                        if key in large_number_keys:
                            numerical_stats[key] = format_large_number(value)
                        else:
                            numerical_stats[key] = value
                    elif value is not None and isinstance(value, list):
                        # Keep list data for revenue projections
                        if key in ['revenue_projections']:
                            numerical_stats[key] = value
                    elif value is not None and isinstance(value, str):
                        # Try to convert string numbers to float
                        clean_value = str(value).replace('$', '').replace(',', '').replace('%', '').strip()
                        # Check if it's a valid number (including decimals and negative numbers)
                        if clean_value and (clean_value.replace('.', '').replace('-', '').isdigit() or 
                                           (clean_value.count('.') == 1 and clean_value.replace('.', '').replace('-', '').isdigit())):
                            converted_value = float(clean_value)
                            # Apply formatting for large numbers
                            if key in large_number_keys:
                                numerical_stats[key] = format_large_number(converted_value)
                            else:
                                numerical_stats[key] = converted_value
                except (ValueError, AttributeError, TypeError) as e:
                    # Log the conversion failure for debugging
                    logger.debug(f"Failed to convert '{value}' to number for key '{key}': {e}")
                    continue
            
            # Add non-numerical but important categorical data
            numerical_stats.update({
                'sector': startup_data.get('sector'),
                'stage': startup_data.get('stage'),
                'geography': startup_data.get('geography'),
                'recommendation_tier': weighted_scores.get('recommendation', {}).get('tier'),
            })
            
            return numerical_stats
            
        except Exception as e:
            logger.error(f"Error extracting numerical stats: {e}")
            # Return minimal stats in case of error
            return {
                'overall_score': weighted_scores.get('overall_score'),
                'sector': startup_data.get('sector'),
                'stage': startup_data.get('stage'),
                'recommendation_tier': weighted_scores.get('recommendation', {}).get('tier'),
            }

    def _extract_revenue_projections(self, startup_data: Dict) -> List[Dict[str, Any]]:
        """Extract revenue projections data from startup data"""
        try:
            # Get financials data
            financials = startup_data.get('financials', {})
            if not isinstance(financials, dict):
                financials = {}
            
            # Also check synthesized data
            synthesized_financials = startup_data.get('synthesized_data', {}).get('financials', {})
            if not isinstance(synthesized_financials, dict):
                synthesized_financials = {}
            
            # Combine both sources, prioritizing synthesized data
            combined_financials = {**financials, **synthesized_financials}
            
            # Look for revenue projections
            revenue_projections = combined_financials.get('revenue_projections')
            
            # If no direct projections found, try to construct from other revenue-related fields
            if not revenue_projections or not isinstance(revenue_projections, list):
                # Look for any field that might contain year-based revenue data
                potential_fields = [
                    'revenue_forecast',
                    'annual_revenue_projections',
                    'revenue_model',
                    'projected_revenue',
                    'historical_revenue',
                    'revenue_by_year'
                ]
                
                for field in potential_fields:
                    field_data = combined_financials.get(field)
                    if isinstance(field_data, list) and len(field_data) > 0:
                        # Check if it looks like year-based revenue data
                        if all(isinstance(item, dict) and 'year' in item and 'number' in item for item in field_data):
                            revenue_projections = field_data
                            break
            
            # Validate and format the data
            if revenue_projections and isinstance(revenue_projections, list):
                formatted_projections = []
                for item in revenue_projections:
                    if isinstance(item, dict) and 'year' in item and 'number' in item:
                        try:
                            year = int(item['year'])
                            number = float(item['number']) if item['number'] is not None else None
                            if number is not None:  # Reasonable year range
                                formatted_projections.append({
                                    'year': year,
                                    'number': number
                                })
                        except (ValueError, TypeError):
                            continue
                
                # Sort by year and return
                if formatted_projections:
                    return sorted(formatted_projections, key=lambda x: x['year'])
            
            # Return empty list if no valid data found
            return []
            
        except Exception as e:
            logger.error(f"Error extracting revenue projections: {e}")
            return []

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
                    candidate_count=1
                )

                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self._model.models.generate_content(model="gemini-2.5-flash",contents = [prompt], config=generation_config)
                )
                
                if response and hasattr(response, 'text') and response.text:
                    return sanitize_for_frontend(response.text.strip())
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
        
        # Extract key metrics for better context
        financials = startup_data.get('financials', {}) or startup_data.get('synthesized_data', {}).get('financials', {})
        market = startup_data.get('market', {}) or startup_data.get('synthesized_data', {}).get('market', {})
        team = startup_data.get('team', {}) or startup_data.get('synthesized_data', {}).get('team', {})
        traction = startup_data.get('traction', {}) or startup_data.get('synthesized_data', {}).get('traction', {})
        
        # Format key metrics clearly
        startup_data_str = f"""
            Revenue: ${financials.get('revenue', 'Not disclosed')}
            Growth Rate: {financials.get('growth_rate', 'Not disclosed')}%
            Burn Rate: ${financials.get('burn_rate', 'Not disclosed')}/month
            Funding Raised: ${financials.get('funding_raised', 'Not disclosed')}
            Team Size: {team.get('size', 'Not disclosed')}
            Customers: {traction.get('customers', 'Not disclosed')}
            Market Size: ${market.get('size', 'Not disclosed')}
            Competitors: {', '.join(market.get('competitors', [])[:3]) if market.get('competitors') else 'Not disclosed'}
        """
        
        # Format benchmark results
        percentiles = benchmark_results.get('percentiles', {})
        benchmark_str = f"""
            Overall Score: {benchmark_results.get('overall_score', {}).get('score', 'N/A')}/100
            Revenue Percentile: {percentiles.get('revenue', {}).get('percentile', 'N/A')}th
            Growth Percentile: {percentiles.get('growth_rate', {}).get('percentile', 'N/A')}th  
            Team Size Percentile: {percentiles.get('team_size', {}).get('percentile', 'N/A')}th
        """
        
        prompt = f"""
            You are a senior investment partner preparing a comprehensive deal note for {company_name}. Generate a structured JSON response with detailed investment analysis.

            COMPANY DATA:
            - Name: {company_name}
            - Sector: {sector} 
            - Stage: {stage}
            - Investment Score: {overall_score:.1f}/10
            - Recommendation: {recommendation_tier}
            - Risk Score: {risk_score:.1f}/10

            KEY METRICS:
            {startup_data_str}

            RISK SUMMARY:
            {risk_summary}

            BENCHMARKS:
            {benchmark_str}

            Generate a JSON response with the following exact structure:

            {{
            "company_description": "A comprehensive 100-150 word description of the company covering what they do, their business model, target market, key products/services, competitive advantages, and current market position in the {sector} sector.",
            
            "deal_summary": "Generate a deal summary as a JSON array of strings. Each string in the array must be a separate key point and should be between 40 and 60 words long. The array should contain exactly 3 strings. Each string must cover different aspects of the investment opportunity, key strengths, market position, financial performance, team capabilities, and the final recommendation with a clear rationale.",
            
            "positive_insights": [
                "High revenue growth",
                "Strong market position", 
                "Experienced team",
                "Scalable business model"
            ],
            
            "negative_insights": [
                "High competition",
                "Limited runway",
                "Market saturation risk",
                "Regulatory challenges"
            ],
            
            "detailed_analysis": {{
                "investment_thesis": {{
                "market_opportunity": "Analysis of market size, growth trends, and timing for {sector} sector",
                "competitive_position": "Assessment of differentiation, competitive moats, and market positioning",
                "team_execution": "Evaluation of founder/team capabilities and execution track record",
                "financial_performance": "Review of key metrics, unit economics, and growth trajectory",
                "strategic_value": "Exit potential, returns assessment, and strategic fit"
                }},
                
                "financial_analysis": {{
                "revenue_analysis": "Current revenue trajectory and growth patterns",
                "unit_economics": "CAC, LTV, gross margins, and payback period analysis",
                "burn_runway": "Monthly burn rate and runway assessment",
                "funding_history": "Previous rounds, current needs, and use of funds",
                "projections": "Financial forecast assessment and assumptions"
                }},
                
                "market_assessment": {{
                "market_size": "TAM/SAM analysis and addressable opportunity",
                "growth_drivers": "Key market trends and catalysts",
                "competition": "Competitive landscape and positioning analysis",
                "market_timing": "Adoption curve and market readiness assessment"
                }},
                
                "risk_assessment": {{
                "primary_risks": [
                    {{"category": "Market Risk", "description": "Risk description", "likelihood": "Medium", "impact": "High", "mitigation": "Mitigation strategy"}},
                    {{"category": "Execution Risk", "description": "Risk description", "likelihood": "Low", "impact": "Medium", "mitigation": "Mitigation strategy"}},
                    {{"category": "Financial Risk", "description": "Risk description", "likelihood": "Medium", "impact": "High", "mitigation": "Mitigation strategy"}},
                    {{"category": "Competitive Risk", "description": "Risk description", "likelihood": "High", "impact": "Medium", "mitigation": "Mitigation strategy"}},
                    {{"category": "Technology Risk", "description": "Risk description", "likelihood": "Low", "impact": "Medium", "mitigation": "Mitigation strategy"}}
                ]
                }},
                
                "investment_recommendation": {{
                "decision": "{recommendation_tier}",
                "rationale": "3-4 sentence explanation based on investment attractiveness, risk assessment, strategic fit, and market timing",
                "suggested_terms": "Investment size, ownership target, and key terms (if PURSUE recommendation)"
                }},
                
                "due_diligence_priorities": [
                "Financial validation and unit economics verification",
                "Technical architecture and IP assessment", 
                "Customer references and market validation",
                "Team background and reference checks",
                "Legal structure and compliance review"
                ],
                
                "next_steps": [
                "Schedule management presentation",
                "Conduct customer reference calls",
                "Technical deep dive session",
                "Financial model validation",
                "Investment committee presentation"
                ]
            }}
            }}

            CRITICAL REQUIREMENTS:
            1. Return ONLY valid JSON - no markdown, no additional text, no code blocks
            2. Company description must be exactly 100-150 words covering business model, products/services, target market, and competitive position
            3. Deal summary must be exactly 100-150 words covering investment opportunity and recommendation
            4. Positive insights must be 4 keyword-based phrases (e.g., "High revenue growth", "Strong team experience")
            5. Negative insights must be 4 keyword-based phrases (e.g., "High competition", "Limited runway")
            6. Use specific numbers, percentages, and quantitative data from the provided metrics
            7. Base insights on actual company data provided, not generic statements
            8. Ensure all JSON fields are properly formatted and escaped
            9. Include sector-specific insights relevant to {sector} industry
            """
        
        # Ensure prompt doesn't exceed length limit
        if len(prompt) > self.config.max_prompt_length:
            prompt = prompt[:self.config.max_prompt_length] + "\n\n[Content truncated due to length limits]"
        
        return prompt
    
    def _create_success_response(
        self, 
        startup_data: Dict, 
        weighted_scores: Dict, 
        risk_assessment: Dict, 
        content: dict,
        benchmark_results: Dict
    ) -> Dict[str, Any]:
        """Create successful response structure with JSON parsing"""

        # Extract revenue projections data
        revenue_projections = self._extract_revenue_projections(startup_data)
        
        return {
            'generated_at': datetime.now().isoformat(),
            'company_name': startup_data.get('company_name', 'Unknown Company'),
            'company_description': content.get('company_description') if content else None,
            'analyst_recommendation': weighted_scores.get('recommendation', {}).get('tier', 'N/A'),
            'overall_score': weighted_scores.get('overall_score', 0),
            'content': content if content else content,
            'content_type': 'ai_generated_json' if content else 'ai_generated',
            'deal_summary': content.get('deal_summary') if content else None,
            'positive_insights': content.get('positive_insights') if content else None,
            'negative_insights': content.get('negative_insights') if content else None,
            'detailed_analysis': content.get('detailed_analysis') if content else None,
            'revenue_projections': revenue_projections,
            'summary_stats': self._extract_numerical_stats(startup_data, risk_assessment, benchmark_results, weighted_scores),
            'generation_metadata': {
                'model_used': self.config.model_name,
                'temperature': self.config.temperature,
                'generated_successfully': True,
                'json_parsed': content is not None
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
        revenue_projections = self._extract_revenue_projections(startup_data)
        
        return {
            'generated_at': datetime.now().isoformat(),
            'company_name': startup_data.get('company_name', 'Unknown Company'),
            'company_description': fallback_content.get('company_description'),
            'analyst_recommendation': weighted_scores.get('recommendation', {}).get('tier', 'N/A'),
            'overall_score': weighted_scores.get('overall_score', 0),
            'content': fallback_content,
            'content_type': 'fallback_summary',
            'error': f'AI generation failed: {error_message}',
            'deal_summary': fallback_content.get('deal_summary'),
            'positive_insights': fallback_content.get('positive_insights'),
            'negative_insights': fallback_content.get('negative_insights'),
            'detailed_analysis': fallback_content.get('detailed_analysis'),
            'revenue_projections': revenue_projections,
            'summary_stats': self._extract_numerical_stats(startup_data, {}, {'percentiles': {}}, weighted_scores),
            'generation_metadata': {
                'model_used': 'fallback',
                'generated_successfully': False,
                'error': error_message,
                'json_parsed': True
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
    
    def _generate_fallback_summary(self, startup_data: Dict, weighted_scores: Dict) -> Dict[str, Any]:
        """Generate enhanced fallback summary in JSON format when AI generation fails"""
        
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
        
        # Generate company description
        description = startup_data.get('description', '')
        if not description or len(description.split()) < 50:
            # Generate a basic description if none exists or it's too short
            description = f"{company_name} is a {sector} company operating in the {stage} stage. The company has established operations with a team of {team_size} members and has raised {funding_raised} in funding. Based on available data, the company shows {revenue} in revenue with {growth_rate} growth rate. The company operates in the {sector} sector and is positioned for growth in their target market. Additional company details and business model information require further analysis to provide a comprehensive overview."
        
        # Ensure description is 100-150 words
        desc_words = description.split()
        if len(desc_words) > 150:
            description = ' '.join(desc_words[:150]) + '...'
        elif len(desc_words) < 100:
            # Pad with additional context
            description += f" The company is based in {startup_data.get('geography', 'undisclosed location')} and was founded in {startup_data.get('founded', 'unknown year')}. Further business model analysis and market positioning details are needed for comprehensive evaluation."
        
        # Generate fallback JSON structure
        fallback_json = {
            "company_description": description,
            "deal_summary": f"{company_name} is a {sector} company in the {stage} stage with an overall score of {score:.1f}/10. The company shows {revenue} in revenue with {growth_rate} growth rate. Our recommendation is {recommendation} based on current analysis. {reasoning[:100]}...",
            
            "positive_insights": [
                "Company established in sector",
                "Has revenue metrics available", 
                "Team size documented",
                "Funding history tracked"
            ],
            
            "negative_insights": [
                "Limited data available",
                "AI analysis unavailable",
                "Incomplete assessment",
                "Requires manual review"
            ],
            
            "detailed_analysis": {
                "investment_thesis": {
                    "market_opportunity": f"Operating in {sector} sector with {stage} stage positioning",
                    "competitive_position": "Position assessment requires additional data",
                    "team_execution": f"Team size: {team_size}, execution track record needs validation",
                    "financial_performance": f"Revenue: {revenue}, Growth: {growth_rate}, requires detailed analysis",
                    "strategic_value": "Strategic assessment pending comprehensive analysis"
                },
                
                "financial_analysis": {
                    "revenue_analysis": f"Current revenue reported as {revenue}",
                    "unit_economics": "Unit economics analysis requires additional data",
                    "burn_runway": "Burn rate and runway assessment pending",
                    "funding_history": f"Funding raised: {funding_raised}",
                    "projections": "Financial projections require validation"
                },
                
                "market_assessment": {
                    "market_size": f"Market analysis for {sector} sector pending",
                    "growth_drivers": "Market growth drivers require research",
                    "competition": "Competitive analysis needs completion",
                    "market_timing": "Market timing assessment requires additional data"
                },
                
                "risk_assessment": {
                    "primary_risks": [
                        {"category": "Data Risk", "description": "Limited data availability", "likelihood": "High", "impact": "Medium", "mitigation": "Conduct comprehensive due diligence"},
                        {"category": "Analysis Risk", "description": "AI analysis unavailable", "likelihood": "High", "impact": "Medium", "mitigation": "Manual analysis required"},
                        {"category": "Market Risk", "description": "Market position unclear", "likelihood": "Medium", "impact": "Medium", "mitigation": "Market research needed"},
                        {"category": "Financial Risk", "description": "Financial metrics incomplete", "likelihood": "Medium", "impact": "High", "mitigation": "Financial validation required"},
                        {"category": "Assessment Risk", "description": "Incomplete evaluation", "likelihood": "High", "impact": "High", "mitigation": "Full analysis when AI available"}
                    ]
                },
                
                "investment_recommendation": {
                    "decision": recommendation,
                    "rationale": reasoning,
                    "suggested_terms": "Investment terms pending comprehensive analysis"
                },
                
                "due_diligence_priorities": [
                    "Complete financial data collection and validation",
                    "Conduct comprehensive market analysis", 
                    "Validate team background and capabilities",
                    "Assess competitive positioning",
                    "Re-run AI analysis when available"
                ],
                
                "next_steps": [
                    "Gather additional company data",
                    "Schedule management presentation",
                    "Conduct market research",
                    "Validate financial metrics",
                    "Re-generate analysis with AI when available"
                ]
            }
        }
        
        return fallback_json