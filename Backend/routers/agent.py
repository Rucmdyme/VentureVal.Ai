# routers/agent.py
from fastapi import APIRouter, HTTPException
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import json
import logging
import asyncio
import re

from models.schemas import ChatRequest, ChatResponse
from models.database import get_firestore_client
from utils.ai_client import monitor_usage, configure_gemini
from settings import PROJECT_ID, GCP_REGION
from utils.enhanced_text_cleaner import sanitize_for_frontend, clean_response_dict, clean_response_text


router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)

# Enhanced question categories for better follow-up generation
QUESTION_CATEGORIES = {
    'financial': [
        'revenue', 'profit', 'cash', 'funding', 'valuation', 'burn', 'runway', 'margins',
        'unit economics', 'cac', 'ltv', 'arr', 'mrr', 'profitability', 'financial',
        'money', 'capital', 'investment', 'returns', 'metrics', 'kpi'
    ],
    'risk': [
        'risk', 'threat', 'challenge', 'problem', 'concern', 'issue', 'weakness',
        'vulnerability', 'danger', 'failure', 'downside', 'mitigation', 'contingency'
    ],
    'market': [
        'market', 'competition', 'competitor', 'industry', 'sector', 'tam', 'sam', 'som',
        'demand', 'opportunity', 'landscape', 'positioning', 'share', 'trends',
        'customers', 'segments', 'addressable'
    ],
    'team': [
        'team', 'founder', 'management', 'leadership', 'experience', 'background',
        'ceo', 'cto', 'personnel', 'hiring', 'talent', 'expertise', 'skills',
        'advisory', 'board', 'governance'
    ],
    'growth': [
        'growth', 'scale', 'expansion', 'potential', 'future', 'forecast', 'scaling',
        'trajectory', 'acceleration', 'momentum', 'traction', 'adoption', 'viral'
    ],
    'product': [
        'product', 'technology', 'innovation', 'differentiation', 'advantage', 'features',
        'platform', 'solution', 'offering', 'development', 'roadmap', 'ip', 'patent',
        'competitive advantage', 'moat', 'defensibility'
    ],
    'investment': [
        'investment', 'returns', 'exit', 'ipo', 'acquisition', 'multiple', 'irr',
        'portfolio', 'strategy', 'thesis', 'due diligence', 'terms', 'structure'
    ],
    'traction': [
        'traction', 'customers', 'users', 'adoption', 'retention', 'churn', 'engagement',
        'partnerships', 'sales', 'pipeline', 'conversion', 'acquisition'
    ]
}

@router.post("/chat", response_model=ChatResponse)
@monitor_usage("gemini_requests")
async def agent_chat(request: ChatRequest):
    """Handle agent conversations with comprehensive analysis context"""
    
    analysis_data = None
    
    try:
        # Enhanced input validation
        if not request.analysis_id or not request.analysis_id.strip():
            raise HTTPException(status_code=400, detail="Analysis ID is required")
        
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="Question is required")
        
        if len(request.question.strip()) > 1000:
            raise HTTPException(status_code=400, detail="Question too long (max 1000 characters)")
        
        # Get analysis context asynchronously (single fetch)
        analysis_data = await get_analysis_data(request.analysis_id.strip())
        
        # Build enhanced context prompt with chat history
        context_prompt = await build_context_prompt(analysis_data, request.chat_history)
        
        # Generate AI response with suggestions in a single API call
        try:
            ai_result = await generate_ai_response_with_suggestions(context_prompt, request.question.strip(), analysis_data, request.chat_history)
            return ChatResponse(
                response=ai_result['response'],
                suggested_questions=ai_result['suggested_questions'],
                analysis_id=request.analysis_id
            )
        except Exception as ai_error:
            logger.error(f"AI generation failed: {str(ai_error)}")
            # Return default response when AI fails (using already fetched analysis_data)
            default_result = generate_default_response(request.question.strip(), analysis_data)
            return ChatResponse(
                response=default_result['response'],
                suggested_questions=default_result['suggested_questions'],
                analysis_id=request.analysis_id
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in agent_chat: {str(e)}")
        # Return default response for any unexpected errors
        if analysis_data:
            # Use already fetched analysis data if available
            default_result = generate_default_response(request.question.strip(), analysis_data)
            return ChatResponse(
                response=default_result['response'],
                suggested_questions=default_result['suggested_questions'],
                analysis_id=request.analysis_id
            )
        else:
            # Final fallback if analysis data was never fetched
            return ChatResponse(
                response="I apologize, but I'm currently unable to provide a detailed response due to technical difficulties. However, I'm here to help you analyze this investment opportunity once the issue is resolved.",
                suggested_questions=[
                    "What are the key financial metrics for this company?",
                    "What are the main investment risks to consider?",
                    "How does this opportunity compare to market benchmarks?",
                    "What is the overall investment recommendation?"
                ],
                analysis_id=request.analysis_id
            )

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
            
        if analysis_data.get('progress') < 30:
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

async def build_context_prompt(analysis_data: Dict[str, Any], chat_history: Optional[List[Dict]] = None) -> str:
    """Build comprehensive context prompt for AI with enhanced investment focus and chat history"""
    
    try:
        # Safely extract data with defaults
        company_name = analysis_data.get('company_name', 'Unknown Company')
        processed_data = analysis_data.get('processed_data', {})
        synthesized_data = processed_data.get('synthesized_data', {})
        
        # Extract key metrics
        sector = synthesized_data.get('sector', 'Unknown Sector')
        stage = synthesized_data.get('stage', 'Unknown Stage')
        geography = synthesized_data.get('geography', 'Unknown')
        
        # Extract financial data
        financials = synthesized_data.get('financials', {})
        market = synthesized_data.get('market', {})
        team = synthesized_data.get('team', {})
        traction = synthesized_data.get('traction', {})
        
        # Extract analysis scores
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
        
        # Format top risks
        top_risks_formatted = format_top_risks(risk_assessment)
        
        # Format benchmark performance
        benchmarking = analysis_data.get('benchmarking', {})
        benchmark_performance = format_benchmark_performance(benchmarking)
        
        # Format founders list (stored as strings with titles and backgrounds)
        founders_list = "Not disclosed"
        if team.get('founders'):
            founders = team.get('founders', [])
            if isinstance(founders, list) and founders:
                founders_list = '; '.join([str(f) for f in founders])
        
        # Format competitors
        competitors_list = "Not identified"
        if market.get('competitors'):
            competitors = market.get('competitors', [])
            if isinstance(competitors, list) and competitors:
                competitors_list = ', '.join(competitors)
        
        # Extract additional stored data
        product = synthesized_data.get('product', {})
        operations = synthesized_data.get('operations', {})
        funding = synthesized_data.get('funding', {})
        
        # Format chat history if provided
        chat_history_context = ""
        if chat_history and len(chat_history) > 0:
            # Get last 10 conversations
            recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
            chat_history_context = "\nRECENT CONVERSATION HISTORY:\n"
            for i, message in enumerate(recent_history, 1):
                role = message.get('role', 'unknown')
                content = message.get('content', '')
                if role == 'assistant':
                    chat_history_context += f"            {i}. Dealio: {content}\n"
                elif role == 'user':
                    chat_history_context += f"            {i}. Investor: {content}\n"
            chat_history_context += "\n"

        # Build context using only stored data
        context_prompt = f"""
            You are a senior investment analyst and startup advisor with 15+ years of experience in venture capital. You have conducted a comprehensive analysis of {company_name} and are now answering investor questions with professional expertise. You are a friendly, approachable investment professional who maintains warm relationships while providing data-driven insights.
            {chat_history_context}

            COMPANY PROFILE:
            • Company: {company_name}
            • Sector: {sector}
            • Stage: {stage}
            • Geography: {geography}
            • Founded: {synthesized_data.get('founded', 'Not disclosed')}
            • Description: {synthesized_data.get('description', 'Not available')}

            INVESTMENT ANALYSIS SUMMARY:
            • Overall Investment Score: {f"{overall_score:.1f}/10" if overall_score is not None else "N/A"}
            • Risk Assessment: {f"{risk_score:.1f}/10" if risk_score is not None else "N/A"} (lower is better)
            • Investment Recommendation: {tier}
            • Investment Rationale: {rationale}

            FINANCIAL METRICS (from stored data):
            • Annual Revenue: ${format_currency(financials.get('revenue'))}
            • Monthly Revenue (MRR): ${format_currency(financials.get('monthly_revenue'))}
            • Growth Rate: {format_percentage(financials.get('growth_rate'))} annually
            • Monthly Growth Rate: {format_percentage(financials.get('monthly_growth_rate'))}
            • Monthly Burn Rate: ${format_currency(financials.get('burn_rate'))}/month
            • Runway: {financials.get('runway_months', 'Not disclosed')} months
            • Total Funding Raised: ${format_currency(financials.get('funding_raised'))}
            • Current Round: ${format_currency(financials.get('funding_seeking'))}
            • Valuation: ${format_currency(financials.get('valuation'))}
            • Gross Margin: {format_percentage(financials.get('gross_margin'))}
            • CAC: ${format_currency(financials.get('cac'))}
            • LTV: ${format_currency(financials.get('ltv'))}
            • LTV/CAC Ratio: {financials.get('ltv_cac_ratio', 'Not disclosed')}

            MARKET DATA (from stored data):
            • Total Addressable Market (TAM): ${format_currency(market.get('size'))}
            • Serviceable Addressable Market (SAM): ${format_currency(market.get('sam'))}
            • Serviceable Obtainable Market (SOM): ${format_currency(market.get('som'))}
            • Target Customer Segment: {market.get('target_segment', 'Not specified')}
            • Key Competitors: {competitors_list}
            • Market Growth Rate: {format_percentage(market.get('growth_rate'))} annually
            • Competitive Positioning: {market.get('competitive_positioning', 'Not specified')}

            TEAM DATA (from stored data):
            • Team Size: {team.get('size', 'Not disclosed')} employees
            • Founders: {founders_list}
            • Key Hires: {len(team.get('key_hires', [])) if team.get('key_hires') else 0} key roles identified
            • Advisors: {len(team.get('advisors', [])) if team.get('advisors') else 0} advisors
            • Team Experience: {team.get('team_experience', 'Not specified')}

            TRACTION DATA (from stored data):
            • Paying Customers: {format_number(traction.get('customers'))}
            • Total Users: {format_number(traction.get('users'))}
            • Monthly Active Users: {format_number(traction.get('mau'))}
            • Customer Retention Rate: {format_percentage(traction.get('retention_rate'))}
            • NPS Score: {traction.get('nps_score', 'Not disclosed')}
            • Key Partnerships: {len(traction.get('partnerships', [])) if traction.get('partnerships') else 0} partnerships

            PRODUCT DATA (from stored data):
            • Product Name: {product.get('name', 'Not specified')}
            • Product Stage: {product.get('stage', 'Not specified')}
            • Business Model: {product.get('business_model', 'Not specified')}
            • Competitive Advantage: {product.get('competitive_advantage', 'Not specified')}
            • Technology Stack: {product.get('technology_stack', 'Not specified')}
            • IP Portfolio: {product.get('intellectual_property', 'Not specified')}

            OPERATIONS DATA (from stored data):
            • Go-to-Market Strategy: {operations.get('go_to_market', 'Not specified')}
            • Pricing Strategy: {operations.get('pricing_strategy', 'Not specified')}
            • Distribution Channels: {len(operations.get('distribution_channels', [])) if operations.get('distribution_channels') else 0} channels
            • Unit Economics: {operations.get('unit_economics', 'Not specified')}

            TOP INVESTMENT RISKS:
            {top_risks_formatted}

            BENCHMARK PERFORMANCE:
            {benchmark_performance}

            RESPONSE GUIDELINES:
            1. Answer as an experienced investment professional who has thoroughly analyzed this company
            2. Handle greetings warmly and redirect to investment discussion professionally
            3. For out-of-scope questions, politely explain limitations and redirect to investment topics
            4. Reference ONLY the specific data points from the stored analysis above for investment questions
            5. If data shows "Not disclosed" or "Not specified", acknowledge this limitation
            6. Be direct and actionable - investors need clear, decisive guidance
            7. Frame responses in terms of investment implications and decision-making criteria
            8. Use professional VC terminology and investment frameworks
            9. Consider the company's stage and sector when providing guidance
            10. Always tie insights back to potential returns, risks, and investment attractiveness
            11. Maintain a friendly but professional tone throughout all interactions
        """
                    
        return context_prompt
        
    except Exception as e:
        logger.error(f"Error building context prompt: {str(e)}")
        return f"Limited context available for {analysis_data.get('company_name', 'this company')}."

async def generate_ai_response_with_suggestions(context_prompt: str, question: str, analysis_data: Dict[str, Any], chat_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Generate AI response with suggested questions in a single API call"""
    
    try:
        # Extract key data for context
        company_name = analysis_data.get('company_name', 'this company')
        processed_data = analysis_data.get('processed_data', {})
        synthesized_data = processed_data.get('synthesized_data', {})
        sector = synthesized_data.get('sector', '')
        stage = synthesized_data.get('stage', '')
        
        # Extract scores and recommendation
        risk_score = safe_float_convert(
            analysis_data.get('risk_assessment', {}).get('overall_risk_score', 0)
        )
        overall_score = safe_float_convert(
            analysis_data.get('weighted_scores', {}).get('overall_score', 0)
        )
        recommendation = analysis_data.get('weighted_scores', {}).get('recommendation', {})
        tier = recommendation.get('tier', 'N/A') if isinstance(recommendation, dict) else str(recommendation)
        
        # Categorize current question
        question_category = categorize_question(question)
        
        # Use async executor for AI generation
        def _generate_response():
            configure_gemini()
            model = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=GCP_REGION
            )
            
            # Enhanced prompt with specific instructions for both response and suggestions
            full_prompt = f"""{context_prompt}

                CONVERSATION CONTEXT:
                This is a Q&A session with an investor who is evaluating this company for potential investment. You are a professional investment analyst friend who provides data-driven insights to make informed investment decisions. The investor values CONCISE, FOCUSED answers.
                
                {"IMPORTANT: Review the recent conversation history above between DEALIO(my chatbot) and Investor to maintain context and avoid repeating information already discussed. Build upon previous exchanges naturally." if chat_history and len(chat_history) > 0 else ""}

                INVESTOR QUESTION: "{question}"

                ADDITIONAL CONTEXT FOR SUGGESTIONS:
                - Company: {company_name}
                - Sector: {sector}
                - Stage: {stage}
                - Investment Score: {overall_score:.1f}/10
                - Risk Score: {risk_score:.1f}/10
                - Recommendation: {tier}
                - Question Category: {question_category}

                CRITICAL INSTRUCTION: You must provide BOTH a response to the question AND 4 suggested follow-up questions in a specific JSON format.

                RESPONSE HANDLING GUIDELINES:

                1. GREETINGS & PLEASANTRIES:
                   If the question is a greeting (hello, hi, how are you, good morning, etc.), respond warmly and professionally:
                   - Example: "I'm well, thank you. I'm ready to dive into our discussion regarding [Company Name] and address any questions you have about its investment potential. We have a comprehensive analysis prepared to guide our conversation. Please feel free to begin with your first inquiry."
                   - Always redirect to the investment analysis after acknowledging the greeting
                   - Maintain a friendly but professional investment analyst tone

                2. OUT-OF-SCOPE QUESTIONS:
                   If the question is beyond investment analysis scope (cultural events, personal topics, unrelated subjects, etc.), respond politely:
                   - Acknowledge the question courteously
                   - Clearly state the limitation: "The provided investment analysis for [Company Name] focuses exclusively on the company's financial performance, market position, team, product, and associated investment risks. Information regarding [topic] is outside the scope of this investment analysis and is not available in the provided data."
                   - Redirect with a follow-up: "However, I'd be happy to discuss any aspects of [Company Name]'s investment potential. What specific investment considerations would you like to explore?"
                   - Be polite but firm about scope boundaries

                3. INVESTMENT-RELATED QUESTIONS:
                   For questions within scope, follow the standard analysis approach:
                   - First, identify what specific aspect of the investment the question addresses (financial, risk, market, team, product, etc.)
                   - Reference relevant data points from the comprehensive analysis above
                   - Provide quantitative context and benchmarking where available
                   - Explain the investment implications clearly
                   - Consider the company's stage and sector context
                   - Suggest follow-up considerations if relevant

                RESPONSE REQUIREMENTS:
                • Keep response STRICTLY within 30-150 words - this is critical for user experience
                • For greetings: Be warm, acknowledge, and redirect to investment discussion
                • For out-of-scope: Be polite, explain limitations, and redirect with investment-focused follow-up
                • For investment questions: Answer directly with supporting data
                • Start with a direct, clear response to the question type
                • Support with 1-2 key data points from the analysis when relevant
                • Use concise bullet points if listing multiple items
                • End with one brief actionable insight related to the question
                • If data is missing, briefly acknowledge in 1 sentence
                • Maintain professional investment analyst tone throughout
                • Be precise and eliminate unnecessary words
                • WORD COUNT LIMIT: Maximum 150 words, target 40-130 words
                • IMPORTANT: Complete your response fully within the word limit

                SUGGESTED QUESTIONS REQUIREMENTS:
                Generate 4 highly relevant follow-up questions that an investor would naturally ask next. Focus on:
                1. Investment decision-making factors
                2. Due diligence priorities
                3. Risk assessment and mitigation
                4. Return potential and exit strategy
                5. Competitive positioning and market dynamics
                6. Management team and execution capability

                Requirements for suggestions:
                - Questions should be specific to this company's situation
                - Focus on actionable investment insights
                - Consider the recommendation tier ({tier}) when framing questions
                - Address potential investor concerns
                - Help investors make informed decisions
                - Be professional and direct
                - Avoid questions too similar to the current question
                - Each suggested question must be between 10-30 words maximum
                - Keep questions concise and focused for better user experience

                MANDATORY JSON OUTPUT FORMAT:
                You MUST respond with a valid JSON object in exactly this format:
                {{
                    "response": "Your 30-150 word response to the investor question here",
                    "suggested_questions": [
                        "First suggested follow-up question",
                        "Second suggested follow-up question", 
                        "Third suggested follow-up question",
                        "Fourth suggested follow-up question"
                    ]
                }}

                IMPORTANT: Your entire output must be valid JSON. Do not include any text before or after the JSON object."""
            
                            
            generation_config = types.GenerateContentConfig(
                temperature=0.3,  # Controlled temperature for focused responses
                top_p=0.9,  # Focused token selection for conciseness
                top_k=40,
                candidate_count=1,
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                ]
            )
            
            response = model.models.generate_content(
                model="gemini-2.5-flash",
                contents=[full_prompt],
                config=generation_config
            )
            
            return response.text
        
        response_text = await asyncio.get_event_loop().run_in_executor(None, _generate_response)
        
        if not response_text or not response_text.strip():
            raise HTTPException(status_code=500, detail="AI model returned empty response")
        
        # Parse and validate JSON response
        try:
            response = sanitize_for_frontend(response_text.strip()) 
            validated_suggestions = [] 
            if isinstance(response['suggested_questions'], list):         
                validated_suggestions = response['suggested_questions'][:4]
            if len(validated_suggestions)>=4:
                return response
            
            # Generate context-based default questions if needed
            context_defaults = generate_context_based_defaults(
                question, question_category, tier, overall_score, risk_score, 
                company_name, sector, stage, analysis_data
            )
            validated_suggestions.extend(context_defaults)
            response['suggested_questions'] = validated_suggestions[:4]
            return response
        except Exception as e:
            logger.error(f"Response parsing error: {str(e)}")
            # If parsing fails, raise exception to trigger default response
            raise Exception(f"Failed to parse AI response: {str(e)}")
        
    except Exception as e:
        logger.error(f"AI generation error: {str(e)}")
        # Re-raise the exception to be caught by the calling function
        raise Exception(f"AI generation failed: {str(e)}")

def categorize_question(question: str) -> str:
    """Categorize question to generate relevant follow-ups with weighted scoring"""
    
    question_lower = question.lower()
    category_scores = {}
    
    # Score each category based on keyword matches
    for category, keywords in QUESTION_CATEGORIES.items():
        score = 0
        for keyword in keywords:
            if keyword in question_lower:
                # Give higher weight to longer, more specific keywords
                score += len(keyword.split())
        category_scores[category] = score
    
    # Return category with highest score, or 'general' if no matches
    if category_scores and max(category_scores.values()) > 0:
        return max(category_scores, key=category_scores.get)
    
    return 'general'

def generate_context_based_defaults(current_question: str, question_category: str, tier: str, overall_score: float, 
                                   risk_score: float, company_name: str, sector: str, 
                                   stage: str, analysis_data: Dict[str, Any]) -> List[str]:
    """Generate context-based default questions based on analysis data and question category"""
    
    try:
        # Extract additional context
        processed_data = analysis_data.get('processed_data', {})
        synthesized_data = processed_data.get('synthesized_data', {})
        financials = synthesized_data.get('financials', {})
        suggestions = []
        
        # Investment decision-focused questions based on analysis results
        if tier == 'PASS':
            suggestions.extend([
                "What would need to change to make this investment viable?",
                "Are there any pivot opportunities that could improve the outlook?",
                "What are the key deal-breakers in this analysis?"
            ])
        elif tier == 'PURSUE':
            suggestions.extend([
                "What due diligence priorities should we focus on?",
                "What terms and valuation would be appropriate?",
                "What could derail this promising opportunity?"
            ])
        elif tier == 'CONSIDER':
            suggestions.extend([
                "What additional information would tip the decision?",
                "What are the key risk mitigation strategies?",
                "How does this compare to other pipeline opportunities?"
            ])
        
        # Category-specific intelligent follow-ups
        if question_category == 'financial':
            revenue = financials.get('revenue')
            growth_rate = financials.get('growth_rate')
            burn_rate = financials.get('burn_rate')
            runway = financials.get('runway_months')
            
            if revenue and growth_rate:
                suggestions.append("Is this growth rate sustainable given the current market conditions?")
            if burn_rate and runway:
                suggestions.append("What's the plan for achieving profitability before runway ends?")
            suggestions.extend([
                "How do the unit economics compare to successful companies in this sector?",
                "What are the key assumptions in their financial projections?"
            ])
            
        elif question_category == 'risk':
            suggestions.extend([
                "Which risks pose the greatest threat to investor returns?",
                "How has management addressed similar risks in the past?",
                "What early warning indicators should we monitor post-investment?"
            ])
            
        elif question_category == 'market':
            suggestions.extend([
                f"What's the competitive response likely to be if {company_name} succeeds?",
                "How defensible is their market position long-term?",
                "What market shifts could create new opportunities or threats?"
            ])
            
        elif question_category == 'team':
            suggestions.extend([
                "What key hires are critical for the next growth phase?",
                "How does the team's experience match the execution challenges ahead?",
                "What governance and board composition would be optimal?"
            ])
            
        elif question_category == 'product':
            suggestions.extend([
                "What's the roadmap for maintaining competitive advantage?",
                "How strong is the intellectual property position?",
                "What's the customer feedback on product-market fit?"
            ])
            
        elif question_category == 'growth':
            suggestions.extend([
                "What are the biggest bottlenecks to scaling?",
                "How capital efficient is their growth strategy?",
                "What's the total addressable market they can realistically capture?"
            ])
        
        # Score-based contextual questions
        if overall_score > 7.5:
            suggestions.append("What could cause this high-scoring opportunity to underperform?")
        elif overall_score < 4:
            suggestions.append("What would it take to turn this around?")
        
        if risk_score > 7:
            suggestions.append("How can we structure the investment to mitigate these high risks?")
        elif risk_score < 3:
            suggestions.append("Are we missing any significant risks in this analysis?")
        
        # Stage and sector specific questions
        if stage and sector:
            suggestions.append(f"How does this {stage} {sector} company compare to our best investments?")
        
        # Investment process questions
        suggestions.extend([
            "What's our expected return profile and exit timeline?",
            "How does this fit our portfolio strategy and thesis?",
            "What would be our value-add beyond capital?"
        ])
        
        # Remove duplicates and filter out questions too similar to current
        unique_suggestions = []
        current_words = set(current_question.lower().split())
        
        for suggestion in suggestions:
            suggestion_words = set(suggestion.lower().split())
            # Avoid suggestions too similar to current question
            similarity_ratio = len(current_words.intersection(suggestion_words)) / max(len(current_words), 1)
            if similarity_ratio < 0.5 and suggestion not in unique_suggestions:
                unique_suggestions.append(suggestion)
        
        # Ensure we have good suggestions
        if not unique_suggestions:
            unique_suggestions = [
                "What are the key investment decision factors?",
                "How does this opportunity compare to our investment criteria?",
                "What would be our investment thesis and value proposition?",
                "What due diligence areas need the most attention?"
            ]
        
        return unique_suggestions[:4]
        
    except Exception as e:
        logger.warning(f"Error generating context-based defaults: {str(e)}")
        return [
            "What are the critical investment considerations?",
            "How does this align with our investment strategy?",
            "What additional analysis would be most valuable?",
            "What are the key decision points for this opportunity?"
        ]


def safe_float_convert(value: Any) -> float:
    """Safely convert value to float with fallback"""
    
    if value is None:
        return 0.0
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def format_currency(value: Any) -> str:
    """Format currency values with appropriate units"""
    if value is None:
        return "Not disclosed"
    
    try:
        num_value = float(value)
        if num_value >= 1_000_000_000:
            return f"{num_value / 1_000_000_000:.1f}B"
        elif num_value >= 1_000_000:
            return f"{num_value / 1_000_000:.1f}M"
        elif num_value >= 1_000:
            return f"{num_value / 1_000:.0f}K"
        else:
            return f"{num_value:,.0f}"
    except (ValueError, TypeError):
        return "Not disclosed"

def format_percentage(value: Any) -> str:
    """Format percentage values"""
    if value is None:
        return "Not disclosed"
    
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return "Not disclosed"

def format_number(value: Any) -> str:
    """Format large numbers with appropriate units"""
    if value is None:
        return "Not disclosed"
    
    try:
        num_value = float(value)
        if num_value >= 1_000_000_000:
            return f"{num_value / 1_000_000_000:.1f}B"
        elif num_value >= 1_000_000:
            return f"{num_value / 1_000_000:.1f}M"
        elif num_value >= 1_000:
            return f"{num_value / 1_000:.0f}K"
        else:
            return f"{num_value:,.0f}"
    except (ValueError, TypeError):
        return "Not disclosed"

def format_top_risks(risk_assessment: Dict[str, Any]) -> str:
    """Format top risks for display"""
    if not risk_assessment:
        return "• Risk analysis not available"
    
    try:
        risk_scores = risk_assessment.get('risk_scores', {})
        risk_explanations = risk_assessment.get('risk_explanations', [])
        
        formatted_risks = []
        
        # Get top risks from different categories
        for category, risks in risk_scores.items():
            if isinstance(risks, list) and risks:
                for risk in risks[:1]:  # Top risk per category
                    if isinstance(risk, dict):
                        risk_type = risk.get('type', 'Unknown risk')
                        severity = risk.get('severity', 0)
                        details = risk.get('details', 'No details available')
                        formatted_risks.append(f"• {risk_type.replace('_', ' ').title()} (Severity: {severity}/10): {details}")
        
        # If no structured risks, use explanations
        if not formatted_risks and risk_explanations:
            for explanation in risk_explanations[:3]:
                formatted_risks.append(f"• {str(explanation)}")
        
        if not formatted_risks:
            formatted_risks = ["• Detailed risk analysis not available"]
        
        return '\n'.join(formatted_risks[:5])  # Top 5 risks
        
    except Exception as e:
        logger.warning(f"Error formatting risks: {e}")
        return "• Risk formatting error - raw data available in analysis"

def format_benchmark_performance(benchmarking: Dict[str, Any]) -> str:
    """Format benchmark performance for display"""
    if not benchmarking:
        return "• Benchmark analysis not available"
    
    try:
        percentiles = benchmarking.get('percentiles', {})
        overall_score = benchmarking.get('overall_score', {})
        
        formatted_benchmarks = []
        
        if overall_score:
            score = overall_score.get('score', 'N/A')
            grade = overall_score.get('grade', 'N/A')
            formatted_benchmarks.append(f"• Overall Benchmark Score: {score}/100 (Grade: {grade})")
        
        # Format key percentiles
        key_metrics = ['revenue', 'growth_rate', 'team_size', 'burn_rate', 'valuation']
        for metric in key_metrics:
            if metric in percentiles:
                percentile_data = percentiles[metric]
                if isinstance(percentile_data, dict):
                    percentile = percentile_data.get('percentile', 'N/A')
                    interpretation = percentile_data.get('interpretation', '')
                    metric_name = metric.replace('_', ' ').title()
                    formatted_benchmarks.append(f"• {metric_name}: {percentile}th percentile - {interpretation}")
        
        if not formatted_benchmarks:
            formatted_benchmarks = ["• Detailed benchmark data not available"]
        
        return '\n'.join(formatted_benchmarks[:6])  # Top 6 benchmark insights
        
    except Exception as e:
        logger.warning(f"Error formatting benchmarks: {e}")
        return "• Benchmark formatting error - raw data available in analysis"

def generate_default_response(question: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate default response when AI fails, with context-aware suggestions"""
    
    try:
        # Extract basic company info
        company_name = analysis_data.get('company_name', 'this company')
        processed_data = analysis_data.get('processed_data', {})
        synthesized_data = processed_data.get('synthesized_data', {})
        
        # Extract key metrics for context
        overall_score = safe_float_convert(
            analysis_data.get('weighted_scores', {}).get('overall_score', 0)
        )
        risk_score = safe_float_convert(
            analysis_data.get('risk_assessment', {}).get('overall_risk_score', 0)
        )
        recommendation = analysis_data.get('weighted_scores', {}).get('recommendation', {})
        tier = recommendation.get('tier', 'N/A') if isinstance(recommendation, dict) else str(recommendation)
        
        sector = synthesized_data.get('sector', 'Unknown')
        stage = synthesized_data.get('stage', 'Unknown')
        
        # Categorize the question to provide relevant context
        question_category = categorize_question(question)
        
        # Generate contextual default response
        default_response = f"I apologize, but I'm currently experiencing technical difficulties providing a detailed response to your question about {company_name}. However, I have comprehensive analysis data available and will be able to assist you shortly. The analysis shows this is a {tier.lower()} opportunity with an overall score of {overall_score:.1f}/10."
        
        # Generate context-aware suggested questions based on analysis data
        suggested_questions = generate_context_based_defaults(
            question, question_category, tier, overall_score, risk_score,
            company_name, sector, stage, analysis_data
        )
        
        # Ensure we have exactly 4 suggestions
        if len(suggested_questions) < 4:
            # Add generic investment questions if needed
            generic_questions = [
                f"What are the key strengths of {company_name}?",
                f"What are the main risks associated with {company_name}?",
                f"How does {company_name} compare to competitors?",
                f"What is the investment thesis for {company_name}?",
                "What are the financial highlights from the analysis?",
                "What market opportunities does this company address?",
                "What is the management team's track record?",
                "What are the growth prospects and scalability factors?"
            ]
            
            # Add unique questions not already in suggestions
            for q in generic_questions:
                if len(suggested_questions) >= 4:
                    break
                if q not in suggested_questions:
                    suggested_questions.append(q)
        
        return {
            'response': default_response,
            'suggested_questions': suggested_questions[:4]
        }
        
    except Exception as e:
        logger.error(f"Error generating default response: {str(e)}")
        # Ultimate fallback
        return {
            'response': "I apologize, but I'm currently unable to provide a detailed response due to technical difficulties. However, I'm here to help you analyze this investment opportunity once the issue is resolved.",
            'suggested_questions': [
                "What are the key financial metrics for this company?",
                "What are the main investment risks to consider?",
                "How does this opportunity compare to market benchmarks?",
                "What is the overall investment recommendation?"
            ]
        }
