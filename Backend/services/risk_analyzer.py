# services/risk_analyzer.py
import asyncio
from typing import Dict, List, Optional, Any
import json
import logging
from google import genai
from utils.ai_client import configure_gemini
from settings import PROJECT_ID, GCP_REGION
from utils.enhanced_text_cleaner import sanitize_for_frontend
from utils.helpers import db_insert
from constants import Collections

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    def __init__(self):
        """Initialize risk analyzer with proper API configuration"""
        
        # Configure Gemini API
        configure_gemini()
        
        # Risk category weights for overall scoring
        self.risk_weights = {
            'financial': 0.3,
            'market': 0.25,
            'team': 0.2,
            'product': 0.15,
            'operational': 0.1
        }
        
        # Risk severity thresholds
        self.severity_thresholds = {
            'low': (0, 3),
            'medium': (4, 6),
            'high': (7, 10)
        }
        
    async def analyze_risks(self, analysis_id, startup_data: Dict) -> Dict:
        """Comprehensive risk assessment across 5 categories with AI-first approach"""
        risk_data = {}
        
        if not startup_data:
            risk_data =  {
                'error': 'No startup data provided for risk analysis',
                'risk_scores': {},
                'overall_risk_score': 0,
                'risk_explanations': []
            }
        
        else:
            try:
                # AI-first approach: Try AI analysis for each category first
                risk_analysis_tasks = [
                    self._analyze_category_risks_ai_first(startup_data, "financial"),
                    self._analyze_category_risks_ai_first(startup_data, "market"),
                    self._analyze_category_risks_ai_first(startup_data, "team"),
                    self._analyze_category_risks_ai_first(startup_data, "product"),
                    self._analyze_category_risks_ai_first(startup_data, "operational")
                ]
                
                # Execute all risk analysis concurrently
                risk_results = await asyncio.gather(*risk_analysis_tasks, return_exceptions=True)
                
                # Process results and handle any exceptions
                risks = {}
                categories = ['financial', 'market', 'team', 'product', 'operational']
                
                for i, (category, result) in enumerate(zip(categories, risk_results)):
                    if isinstance(result, Exception):
                        logger.error(f"Error analyzing {category} risks: {result}")
                        # Use fallback risks for this category
                        risks[category] = self._generate_fallback_risks(category, startup_data)
                    else:
                        risks[category] = result

                # Simple deduplication across categories (keep risk in first category it appears)
                risks = self._simple_deduplicate_across_categories(risks)
                
                # Calculate overall risk score
                overall_risk = self.calculate_overall_risk(risks)
                
                # Generate risk explanations
                risk_explanations = await self.generate_risk_explanations(risks)
                
                # Calculate additional risk metrics
                risk_summary = self.calculate_risk_summary(risks)
                
                risk_data = {
                    'risk_scores': risks,
                    'overall_risk_score': overall_risk,
                    'risk_explanations': risk_explanations,
                    'risk_summary': risk_summary,
                    'analysis_metadata': {
                        'categories_analyzed': len(categories),
                        'total_risks_identified': sum(len(risk_list) for risk_list in risks.values()),
                        'high_severity_risks': sum(
                            len([r for r in risk_list if r.get('severity', 0) >= 7]) 
                            for risk_list in risks.values()
                        )
                    }
                }
            
            except Exception as e:
                logger.error(f"Risk analysis failed: {e}")
                risk_data = {
                    'error': f'Risk analysis failed: {str(e)}',
                    'risk_scores': {},
                    'overall_risk_score': 10,  # Maximum risk due to analysis failure
                    'risk_explanations': ['Risk analysis could not be completed']
                }
        await db_insert(analysis_id, Collections.RISK_ANALYSIS, risk_data)
        return risk_data

    def _generate_fallback_risks(self, category: str, data: Dict) -> List[Dict]:
        """Generate fallback risks when AI analysis fails or returns insufficient risks"""
        
        risks = []
        
        try:
            if category == "financial":
                risks.extend(self._generate_financial_fallback_risks(data))
            elif category == "market":
                risks.extend(self._generate_market_fallback_risks(data))
            elif category == "team":
                risks.extend(self._generate_team_fallback_risks(data))
            elif category == "product":
                risks.extend(self._generate_product_fallback_risks(data))
            elif category == "operational":
                risks.extend(self._generate_operational_fallback_risks(data))
            
            # Ensure we have at least 3 risks
            if len(risks) < 3:
                risks.append({
                    'type': f'Insufficient {category.title()} Data',
                    'severity': 4,
                    'details': f"Limited {category} information available for comprehensive risk assessment",
                    'impact': 'medium',
                    'likelihood': 'medium',
                    'mitigation': f"Provide more detailed {category} metrics and documentation",
                    'investor_concern': f"Cannot fully assess {category} risks due to data limitations"
                })
            
        except Exception as e:
            logger.error(f"Error generating fallback risks for {category}: {e}")
            # Return basic fallback risks
            risks = [{
                'type': f'{category.title()} Analysis Error',
                'severity': 5,
                'details': f"Could not complete {category} risk analysis",
                'impact': 'medium'
            }]
        
        return risks[:5]  # Cap at 5 risks per category

    def _generate_financial_fallback_risks(self, data: Dict) -> List[Dict]:
        """Generate financial fallback risks"""
        risks = []
        
        # Get financial data with safe access
        financials = data.get('financials', {}) or data.get('synthesized_data', {}).get('financials', {})
        
        # Revenue and growth rate validation
        revenue = self._safe_numeric_get(financials, 'revenue')
        growth_rate = self._safe_numeric_get(financials, 'growth_rate')
        burn_rate = self._safe_numeric_get(financials, 'burn_rate')
        funding_raised = self._safe_numeric_get(financials, 'funding_raised')
        
        # Runway analysis
        if burn_rate is not None and burn_rate > 0 and funding_raised is not None:
            runway_months = funding_raised / burn_rate
            
            if runway_months < 6:
                risks.append({
                    'type': 'Critical Runway Shortage',
                    'severity': 10,
                    'details': f"Critical: Only {runway_months:.1f} months of runway remaining",
                    'impact': 'critical',
                    'likelihood': 'high',
                    'mitigation': 'Secure immediate funding or drastically reduce burn rate',
                    'investor_concern': 'High risk of company failure due to cash shortage'
                })
            elif runway_months < 12:
                risks.append({
                    'type': 'Short Financial Runway',
                    'severity': 8,
                    'details': f"Short runway: {runway_months:.1f} months remaining",
                    'impact': 'high',
                    'likelihood': 'high',
                    'mitigation': 'Accelerate fundraising efforts and optimize cash flow',
                    'investor_concern': 'Limited time to achieve milestones before next funding round'
                })
        

        # Revenue vs burn rate mismatch
        if revenue is not None and burn_rate is not None and revenue > 0:
            revenue_coverage = (revenue * 12) / burn_rate if burn_rate > 0 else float('inf')
            if revenue_coverage < 0.3:  # Revenue covers less than 30% of burn
                risks.append({
                    'type': 'Low Revenue Coverage',
                    'severity': 7,
                    'details': f"Annual revenue only covers {revenue_coverage*100:.1f}% of burn rate",
                    'impact': 'high',
                    'likelihood': 'high',
                    'mitigation': 'Increase sales and optimize burn rate.',
                    'investor_concern': 'Long-term sustainability and cash runway are at risk'
                })

        # Revenue analysis
        if revenue is None or revenue == 0:
            risks.append({
                'type': 'No Current Revenue',
                'severity': 7,
                'details': "Company has no reported current revenue",
                'impact': 'high',
                'likelihood': 'high',
                'mitigation': 'Focus on customer acquisition and monetization strategy',
                'investor_concern': 'No proven business model or market validation'
            })
        
        # Growth rate analysis
        if growth_rate is not None:
            if growth_rate > 500:
                risks.append({
                    'type': 'Unrealistic Growth Projections',
                    'severity': 8,
                    'details': f"Growth rate of {growth_rate}% appears unrealistic",
                    'impact': 'high',
                    'likelihood': 'medium',
                    'mitigation': 'Provide detailed justification for growth assumptions',
                    'investor_concern': 'Overly optimistic projections may indicate poor planning'
                })
            elif growth_rate < 0:  # Negative growth
                risks.append({
                    'type': 'Negative Growth Trend',
                    'severity': 7,
                    'details': f"Negative growth rate of {growth_rate}% indicates declining business",
                    'impact': 'high',
                    'likelihood': 'high',
                    'mitigation': 'Revise strategy to address declining metrics',
                    'investor_concern': 'Long-term viability is at risk'
                })
        
                   # Missing financial data risks
        if not any([revenue, burn_rate, funding_raised, growth_rate]):
            risks.append({
                'type': 'Missing Financial Data',
                'severity': 6,
                'details': f"Critical financial metrics are missing or unclear",
                'impact': 'medium',
                'likelihood': 'medium',
                'mitigation': 'Provide full, verified financial statements',
                'investor_concern': 'Inability to assess business health and returns'
            })
        return risks

    def _generate_market_fallback_risks(self, data: Dict) -> List[Dict]:
        """Generate market fallback risks"""
        risks = []
        
        # Get market data with safe access
        market = data.get('market', {}) or data.get('synthesized_data', {}).get('market', {})
        
        # Market size validation
        market_size = self._safe_numeric_get(market, 'size')
        if market_size is not None:
            if market_size > 1e12:  # $1T+
                risks.append({
                    'type': 'Inflated Market Size Claims',
                    'severity': 8,
                    'details': f"Market size of ${market_size/1e9:.0f}B appears extremely inflated",
                    'impact': 'high',
                    'likelihood': 'medium',
                    'mitigation': 'Provide detailed market research and sizing methodology',
                    'investor_concern': 'Unrealistic market assumptions may indicate poor research'
                })
        
        # Competition analysis
        competitors = market.get('competitors', [])
        if isinstance(competitors, list):
            if len(competitors) == 0:
                risks.append({
                    'type': 'No Identified Competitors',
                    'severity': 6,
                    'details': "No competitors identified - may indicate poor market research",
                    'impact': 'medium',
                    'likelihood': 'high',
                    'mitigation': 'Conduct thorough competitive analysis',
                    'investor_concern': 'Lack of market understanding or unrealistic assumptions'
                })
            elif len(competitors) > 15:
                risks.append({
                    'type': 'Highly Competitive Market',
                    'severity': 7,
                    'details': f"Market has {len(competitors)} identified competitors",
                    'impact': 'high',
                    'likelihood': 'high',
                    'mitigation': 'Develop strong differentiation strategy',
                    'investor_concern': 'Difficult to gain market share in crowded space'
                })
        
        # Target market analysis
        target = market.get('target_segment', '')
        if not target or len(target.strip()) < 20:
            risks.append({
                'type': 'Unclear Target Market',
                'severity': 5,
                'details': "Target market definition is unclear or too broad",
                'impact': 'medium',
                'likelihood': 'medium',
                'mitigation': 'Define specific target customer segments',
                'investor_concern': 'Unclear go-to-market strategy'
            })
        
        return risks

    def _generate_team_fallback_risks(self, data: Dict) -> List[Dict]:
        """Generate team fallback risks"""
        risks = []
        
        # Get team data with safe access
        team = data.get('team', {}) or data.get('synthesized_data', {}).get('team', {})
        stage = data.get('stage', '') or data.get('synthesized_data', {}).get('stage', '')
        
        # Team size analysis
        team_size = self._safe_numeric_get(team, 'size')
        stage_lower = stage.lower() if stage else ''
        
        if team_size is not None:
            if 'series_a' in stage_lower and team_size < 5:
                risks.append({
                    'type': 'Small Team For Stage',
                    'severity': 7,
                    'details': f"Team size of {team_size} is small for Series A stage",
                    'impact': 'high',
                    'likelihood': 'high',
                    'mitigation': 'Accelerate hiring of key roles',
                    'investor_concern': 'Insufficient capacity to execute growth plans'
                })
            elif 'series_b' in stage_lower and team_size < 10:
                risks.append({
                    'type': 'Small Team For Stage',
                    'severity': 6,
                    'details': f"Team size of {team_size} may be small for Series B stage",
                    'impact': 'medium',
                    'likelihood': 'high',
                    'mitigation': 'Accelerate hiring of key roles',
                    'investor_concern': 'Insufficient capacity to execute growth plans'
                })
            elif team_size < 2:
                risks.append({
                    'type': 'Insufficient Team Size',
                    'severity': 8,
                    'details': f"Team size of {team_size} is insufficient for startup execution",
                    'impact': 'high',
                    'likelihood': 'high',
                    'mitigation': 'Build core team with complementary skills',
                    'investor_concern': 'High execution risk with minimal team'
                })
            

        
        # Founder analysis
        founders = team.get('founders', [])
        if isinstance(founders, list):
            if len(founders) == 0:
                risks.append({
                    'type': 'No Founders Identified',
                    'severity': 9,
                    'details': "No founders identified in team information",
                    'impact': 'critical',
                    'likelihood': 'high',
                    'mitigation': 'Clarify founding team structure',
                    'investor_concern': 'Unclear leadership and ownership structure'
                })
            elif len(founders) == 1:
                risks.append({
                    'type': 'Single Founder Risk',
                    'severity': 6,
                    'details': "Single founder structure increases key person risk",
                    'impact': 'medium',
                    'likelihood': 'medium',
                    'mitigation': 'Consider bringing on co-founders or key executives',
                    'investor_concern': 'High dependency on single individual'
                })
            elif len(founders) > 4:
                risks.append({
                    'type': 'Too Many Founders',
                    'severity': 5,
                    'details': f"{len(founders)} founders may lead to decision-making conflicts",
                    'impact': 'medium',
                    'likelihood': 'medium',
                    'mitigation': 'Clearly define roles and decision-making processes',
                    'investor_concern': 'Decision making conflicts'
                })
        
        # Key hires analysis
        key_hires = team.get('key_hires', [])
        if isinstance(key_hires, list) and len(key_hires) == 0 and team_size and team_size > 10:
            risks.append({
                'type': 'No Key Hires Identified',
                'severity': 4,
                'details': "No key hires identified despite team size - may indicate weak talent acquisition",
                'impact': 'low',
                'likelihood': 'medium',
                'mitigation': 'Recruit experienced professionals for critical roles',
                'investor_concern': 'May lack specialized expertise for growth'
            })
        
        return risks

    def _generate_product_fallback_risks(self, data: Dict) -> List[Dict]:
        """Generate product fallback risks"""
        risks = []
        
        # Get product data with safe access
        product = data.get('product', {}) or data.get('synthesized_data', {}).get('product', {})
        
        # Competitive advantage analysis
        competitive_advantage = product.get('competitive_advantage', '')
        if not competitive_advantage or len(competitive_advantage.strip()) < 30:
            risks.append({
                'type': 'Unclear Competitive Advantage',
                'severity': 6,
                'details': "Product competitive advantage is unclear or poorly defined",
                'impact': 'medium',
                'likelihood': 'high',
                'mitigation': 'Clearly articulate unique value proposition',
                'investor_concern': 'Difficulty differentiating from competitors'
            })
        
        # Product description analysis
        description = product.get('description', '')
        if not description or len(description.strip()) < 50:
            risks.append({
                'type': 'Insufficient Product Description',
                'severity': 5,
                'details': "Product description is vague or insufficient",
                'impact': 'medium',
                'likelihood': 'medium',
                'mitigation': 'Provide detailed product specifications and roadmap',
                'investor_concern': 'Cannot assess product viability and market fit'
            })
        
        # Product stage analysis
        product_stage = (product.get('stage') or '').lower()
        company_stage = (data.get('stage') or '').lower()
        
        if 'concept' in product_stage or 'idea' in product_stage:
            if 'series_a' in company_stage:
                risks.append({
                    'type': 'Product Stage Mismatch',
                    'severity': 8,
                    'details': "Product still in concept stage but seeking Series A funding",
                    'impact': 'high',
                    'likelihood': 'high',
                    'mitigation': 'Accelerate product development and validation',
                    'investor_concern': 'High risk of product not meeting market needs'
                })
        business_model = product.get('business_model', '')
        if not business_model or len(business_model.strip()) < 20:
            risks.append({
                'type': 'Unclear Business Model',
                'severity': 6,
                'details': "Business model is unclear or not well defined",
                'impact': 'medium',
                'likelihood': 'medium',
                'mitigation': 'Define and validate a clear, sustainable revenue model',
                'investor_concern': 'Unpredictable returns due to a lack of monetization strategy'
            })
        
        return risks

    def _generate_operational_fallback_risks(self, data: Dict) -> List[Dict]:
        """Generate operational fallback risks"""
        risks = []
        
        # Get traction data with safe access
        traction = data.get('traction', {}) or data.get('synthesized_data', {}).get('traction', {})
        
        # Customer vs user analysis
        customers = self._safe_numeric_get(traction, 'customers')
        users = self._safe_numeric_get(traction, 'users')
        
        if users is not None and customers is not None:
            if users > 0 and customers == 0:
                risks.append({
                    'type': 'No Paying Customers',
                    'severity': 6,
                    'details': f"Has {users} users but no paying customers",
                    'impact': 'medium',
                    'likelihood': 'high',
                    'mitigation': 'Develop monetization strategy and pricing model',
                    'investor_concern': 'Unproven ability to generate revenue from users'
                })
            elif users > 0 and customers > 0:
                conversion_rate = customers / users
                if conversion_rate < 0.01:  # Less than 1% conversion
                    risks.append({
                        'type': 'Low Conversion Rate',
                        'severity': 7,
                        'details': f"Very low user-to-customer conversion rate ({conversion_rate*100:.2f}%)",
                        'impact': 'high',
                        'likelihood': 'high',
                        'mitigation': 'Improve product value proposition and pricing strategy',
                        'investor_concern': 'Poor monetization efficiency'
                    })
        
        # Partnership analysis
        partnerships = traction.get('partnerships', [])
        if isinstance(partnerships, list) and len(partnerships) == 0:
            stage = (data.get('stage') or '').lower()
            if 'series_a' in stage or 'series_b' in stage:
                risks.append({
                    'type': 'No Strategic Partnerships',
                    'severity': 4,
                    'details': "No partnerships identified for growth stage company",
                    'impact': 'low',
                    'likelihood': 'medium',
                    'mitigation': 'Develop strategic partnerships for growth',
                    'investor_concern': 'Limited channels for market expansion'
                })
        
        # General operational risk
        if customers is None and users is None:
            risks.append({
                'type': 'Missing Traction Data',
                'severity': 5,
                'details': "No customer or user traction data available",
                'impact': 'medium',
                'likelihood': 'high',
                'mitigation': 'Provide comprehensive traction metrics',
                'investor_concern': 'Cannot assess market validation and growth potential'
            })
        
        return risks


    async def _analyze_category_risks_ai_first(self, data: Dict, category: str) -> List[Dict]:
        """AI-first risk analysis for a specific category with fallback mechanism"""
        
        try:
            # First, try AI analysis
            ai_risks = await self._ai_risk_analysis_for_category(data, category)
            
            # Check if we have enough risks (minimum 3)
            if len(ai_risks) >= 3:
                logger.info(f"AI successfully generated {len(ai_risks)} risks for {category}")
                return ai_risks
            else:
                logger.warning(f"AI only generated {len(ai_risks)} risks for {category}, using fallback")
                # Use fallback mechanism to supplement
                fallback_risks = self._generate_fallback_risks(category, data)
                
                # Combine AI and fallback risks, ensuring no duplicates
                combined_risks = ai_risks.copy()
                
                # Add fallback risks until we have at least 3 total
                for fallback_risk in fallback_risks:
                    if len(combined_risks) >= 3:
                        break
                    # Check for duplicates based on risk type
                    if not any(existing['type'].lower() == fallback_risk['type'].lower() for existing in combined_risks):
                        combined_risks.append(fallback_risk)
                
                return combined_risks
                
        except Exception as e:
            logger.error(f"AI analysis failed for {category}: {e}")
            # Complete fallback to default risk analysis
            return self._generate_fallback_risks(category, data)

    async def _ai_risk_analysis_for_category(self, data: Dict, risk_context: str) -> List[Dict]:
        """Use Gemini AI for advanced risk pattern detection with specific context"""

        try:
            # Prepare data for AI analysis (limit size)
            analysis_data = json.dumps(data, indent=2)[:4000]
            
            # Define context-specific risk frameworks
            risk_frameworks = {
                "financial": {
                    "focus": "FINANCIAL RED FLAGS",
                    "categories": [
                        "- Unrealistic revenue projections or growth rates (>500% annually)",
                        "- Burn rate exceeding revenue by >10x", 
                        "- Runway less than 12 months without clear path to profitability",
                        "- Unit economics that don't make sense (CAC > LTV)",
                        "- Missing or inconsistent financial data",
                        "- Funding amounts that don't align with stage or traction",
                        "- Cash flow negative with no clear path to profitability",
                        "- High customer acquisition costs relative to lifetime value",
                        "- Revenue concentration risk (dependency on few customers)",
                        "- Unrealistic valuation expectations vs financial performance"
                    ]
                },
                "market": {
                    "focus": "MARKET & COMPETITIVE RISKS",
                    "categories": [
                        "- Inflated market size claims (TAM >$1T without justification)",
                        "- No identified competitors (suggests poor market research)",
                        "- Declining or stagnant market growth",
                        "- Unclear target customer definition",
                        "- Competitive advantages that are easily replicable",
                        "- Market timing risks (too early or too late)",
                        "- Saturated market with established players",
                        "- Regulatory barriers to market entry",
                        "- Market size too small to support growth ambitions",
                        "- Customer adoption challenges or long sales cycles"
                    ]
                },
                "team": {
                    "focus": "TEAM & PREVIOUS EXECUTION BY TEAM MEMBERS RISKS",
                    "categories": [
                        "- Single founder without co-founder",
                        "- Team size misaligned with stage (too small for Series A+)",
                        "- Lack of relevant industry experience",
                        "- Missing key roles (CTO for tech company, etc.)",
                        "- High founder/team turnover",
                        "- Inexperienced team for complex market",
                        "- Founder-market fit concerns",
                        "- Key person dependency risks",
                        "- Lack of technical expertise for product development",
                        "- Poor track record of execution or previous failures"
                    ]
                },
                "product": {
                    "focus": "PRODUCT & TECHNOLOGY RISKS",
                    "categories": [
                        "- Product still in concept stage for late-stage funding",
                        "- Unclear value proposition or differentiation",
                        "- Technology risks or dependencies",
                        "- Long development cycles without customer validation",
                        "- Product-market fit concerns",
                        "- Scalability limitations",
                        "- Intellectual property vulnerabilities",
                        "- Technical debt or architecture issues",
                        "- Dependency on third-party platforms or APIs",
                        "- Complex product requiring significant user education"
                    ]
                },
                "operational": {
                    "focus": "OPERATIONAL & TRACTION RISKS",
                    "categories": [
                        "- High user counts but no paying customers",
                        "- Declining growth rates or user engagement",
                        "- Customer concentration risk (>50% revenue from few customers)",
                        "- Poor unit economics or customer retention",
                        "- Lack of organic growth or high churn",
                        "- Vanity metrics without business impact",
                        "- Unclear go-to-market strategy",
                        "- Regulatory or compliance risks",
                        "- Dependency on key partnerships or suppliers",
                        "- Scalability challenges in operations"
                    ]
                }
            }
            
            # Get the appropriate framework
            framework = risk_frameworks.get(risk_context, risk_frameworks["financial"])
            focus_area = framework["focus"]
            risk_categories = "\n".join(framework["categories"])
            
            prompt = f"""
            You are a senior investment analyst conducting {focus_area.lower()} on this startup. Analyze the data for critical investment risks and red flags that could impact returns.

            STARTUP DATA FOR ANALYSIS:
            {analysis_data}

            RISK ANALYSIS FOCUS - {focus_area}:
            {risk_categories}

            Return a JSON array of identified risks with detailed analysis:
            [
                {{
                    "category": "{risk_context}",
                    "type": "Risk Name With Proper Spacing",
                    "severity": "1-10 (10 being deal-breaking)",
                    "details": "specific explanation of the risk with supporting evidence from data",
                    "evidence": "exact data points or metrics that support this risk assessment",
                    "impact": "low|medium|high|critical",
                    "likelihood": "low|medium|high (probability of risk materializing)",
                    "mitigation": "potential ways to address or mitigate this risk",
                    "investor_concern": "why this matters to investors and potential impact on returns"
                }}
            ]

            CRITICAL FORMATTING REQUIREMENTS FOR 'type' FIELD:
            1. Use descriptive phrases with proper spacing (e.g., "Critical Short Runway", "Unrealistic Revenue Projections")
            2. NO underscores (_), NO hyphens (-), NO camelCase
            3. Use title case with spaces between words
            4. Examples: "Missing Financial Data", "High Burn Rate", "Unclear Market Position"
            5. Keep it concise but descriptive (3-12 words maximum)

            ANALYSIS REQUIREMENTS:
            1. ONLY analyze risks related to {focus_area.lower()}
            2. Only identify risks with clear evidence from the provided data
            3. Be specific about what makes each item risky (don't use generic statements)
            4. Quantify risks where possible using actual numbers from the data
            5. Consider stage-appropriate expectations (seed vs Series A standards)
            6. Flag any data inconsistencies or missing critical information
            7. Focus on risks that could significantly impact investment returns or company survival
            8. Generate at least 3 distinct risks for this category ({focus_area.lower()}) if possible.

            Return only the JSON array with risks specifically related to key metric: {risk_context} and focus area: {focus_area.lower()}.
            """
            
            model = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=GCP_REGION
            )
            
            response = await asyncio.to_thread(model.models.generate_content, model="gemini-2.5-flash", contents=[prompt])

            if not response or not hasattr(response, 'text') or not response.text:
                logger.error(f"Empty risk response for {risk_context}")
                return []
            try:
                ai_risks = sanitize_for_frontend(response.text.strip())
            except Exception as error:
                logger.error(f"Response parsing error for risk response for {risk_context}: {str(error)}")
                return []
                    
                    # Validate and add AI-identified risks
            validated_risks = []
            for risk in ai_risks:
                if isinstance(risk, dict) and all(k in risk for k in ['type', 'severity', 'details']):
                    # Ensure severity is within bounds
                    risk['severity'] = max(1, min(10, int(risk.get('severity', 5))))
                    if 'impact' not in risk:
                        risk['impact'] = 'medium'
                    validated_risks.append(risk)
            
            logger.info(f"AI identified {len(validated_risks)} {risk_context} risks")
            return validated_risks
        
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse AI {risk_context} risk response: {e}")
            return []
        except Exception as e:
            logger.warning(f"AI {risk_context} risk analysis failed: {e}")
            return []


    def _simple_deduplicate_across_categories(self, risks: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Simple deduplication to remove exact duplicate risk types across categories"""
        
        seen_risk_types = set()
        deduplicated_risks = {}
        
        # Process categories in priority order
        category_priority = ['financial', 'market', 'team', 'product', 'operational']
        
        for category in category_priority:
            if category not in risks:
                continue
                
            deduplicated_risks[category] = []
            
            for risk in risks[category]:
                risk_type_lower = risk.get('type', '').lower()
                
                # Only add if we haven't seen this exact risk type before
                if risk_type_lower not in seen_risk_types:
                    seen_risk_types.add(risk_type_lower)
                    deduplicated_risks[category].append(risk)
        
        return deduplicated_risks

    def calculate_overall_risk(self, risks: Dict[str, List[Dict]]) -> float:
        """Calculate weighted overall risk score"""
        
        if not risks:
            return 0.0
        
        total_weighted_risk = 0.0
        total_weight = 0.0
        
        for category, risk_list in risks.items():
            if risk_list:
                # Calculate average severity for this category
                category_risk = sum(r.get('severity', 0) for r in risk_list) / len(risk_list)
                
                # Apply weight
                weight = self.risk_weights.get(category, 0.1)
                total_weighted_risk += category_risk * weight
                total_weight += weight
        
        # Normalize by actual weights used
        if total_weight > 0:
            overall_risk = total_weighted_risk / total_weight
        else:
            overall_risk = 0.0
        
        return round(min(10.0, max(0.0, overall_risk)), 2)

    def calculate_risk_summary(self, risks: Dict[str, List[Dict]]) -> Dict:
        """Calculate summary statistics for risks"""
        
        all_risks = []
        for risk_list in risks.values():
            all_risks.extend(risk_list)
        
        if not all_risks:
            return {
                'total_risks': 0,
                'by_severity': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
                'by_category': {},
                'average_severity': 0.0
            }
        
        # Count by severity
        severity_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        for risk in all_risks:
            severity = risk.get('severity', 0)
            if severity <= 3:
                severity_counts['low'] += 1
            elif severity <= 6:
                severity_counts['medium'] += 1
            elif severity <= 9:
                severity_counts['high'] += 1
            else:
                severity_counts['critical'] += 1
        
        # Count by category
        category_counts = {}
        for category, risk_list in risks.items():
            category_counts[category] = len(risk_list)
        
        # Calculate average severity
        avg_severity = sum(r.get('severity', 0) for r in all_risks) / len(all_risks)
        
        return {
            'total_risks': len(all_risks),
            'by_severity': severity_counts,
            'by_category': category_counts,
            'average_severity': round(avg_severity, 2)
        }

    async def generate_risk_explanations(self, risks: Dict[str, List[Dict]]) -> List[str]:
        """Generate human-readable risk explanations"""
        
        explanations = []
        
        try:
            # Focus on high-severity risks
            high_severity_risks = []
            for category, risk_list in risks.items():
                for risk in risk_list:
                    if risk.get('severity', 0) >= 7:
                        high_severity_risks.append((category, risk))
            
            # Sort by severity (highest first)
            high_severity_risks.sort(key=lambda x: x[1].get('severity', 0), reverse=True)
            
            # Generate explanations for top risks
            for category, risk in high_severity_risks[:5]:  # Top 5 risks
                explanation = f"**{category.title()} Risk**: {risk.get('details', 'Unknown risk')}"
                if 'impact' in risk:
                    explanation += f" (Impact: {risk['impact']})"
                explanations.append(explanation)
            
            # Add overall assessment if we have risks
            if high_severity_risks:
                explanations.append(f"**Overall Assessment**: {len(high_severity_risks)} high-severity risks identified across {len(risks)} categories.")
        
        except Exception as e:
            logger.error(f"Error generating risk explanations: {e}")
            explanations = ["Risk explanation generation failed - please review individual risk categories"]
        
        return explanations

    def _safe_numeric_get(self, data: Dict, key: str) -> Optional[float]:
        """Safely extract numeric value from data"""
        try:
            value = data.get(key)
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Try to parse string as number
                cleaned = value.replace(',', '').replace('$', '').replace('%', '')
                return float(cleaned)
            return None
        except (ValueError, TypeError, AttributeError):
            return None