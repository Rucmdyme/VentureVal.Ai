# services/risk_analyzer.py
import asyncio
import os
from typing import Dict, List, Optional, Any
import json
import logging
import google.generativeai as genai
from utils.ai_client import configure_gemini

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
        
    async def analyze_risks(self, startup_data: Dict) -> Dict:
        """Comprehensive risk assessment across 5 categories"""
        
        if not startup_data:
            return {
                'error': 'No startup data provided for risk analysis',
                'risk_scores': {},
                'overall_risk_score': 0,
                'risk_explanations': []
            }
        
        try:
            # Analyze risks across all categories
            risk_analysis_tasks = [
                self.analyze_financial_risks(startup_data),
                self.analyze_market_risks(startup_data),
                self.analyze_team_risks(startup_data),
                self.analyze_product_risks(startup_data),
                self.analyze_operational_risks(startup_data)
            ]
            
            # Execute all risk analyses concurrently
            risk_results = await asyncio.gather(*risk_analysis_tasks, return_exceptions=True)
            
            # Process results and handle any exceptions
            risks = {}
            categories = ['financial', 'market', 'team', 'product', 'operational']
            
            for i, (category, result) in enumerate(zip(categories, risk_results)):
                if isinstance(result, Exception):
                    logger.error(f"Error analyzing {category} risks: {result}")
                    risks[category] = [{
                        'type': 'analysis_error',
                        'severity': 5,
                        'details': f'Error analyzing {category} risks: {str(result)}'
                    }]
                else:
                    risks[category] = result
            
            # Calculate overall risk score
            overall_risk = self.calculate_overall_risk(risks)
            
            # Generate risk explanations
            risk_explanations = await self.generate_risk_explanations(risks, startup_data)
            
            # Calculate additional risk metrics
            risk_summary = self.calculate_risk_summary(risks)
            
            return {
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
            return {
                'error': f'Risk analysis failed: {str(e)}',
                'risk_scores': {},
                'overall_risk_score': 10,  # Maximum risk due to analysis failure
                'risk_explanations': ['Risk analysis could not be completed']
            }

    async def analyze_financial_risks(self, data: Dict) -> List[Dict]:
        """Detect financial inconsistencies and red flags"""
        
        risks = []
        
        try:
            # Get financial data with safe access
            financials = data.get('financials', {}) or data.get('synthesized_data', {}).get('financials', {})
            
            # Revenue and growth rate validation
            revenue = self._safe_numeric_get(financials, 'revenue')
            growth_rate = self._safe_numeric_get(financials, 'growth_rate')
            
            # Unrealistic growth rate check
            if growth_rate is not None:
                if growth_rate > 1000:  # 1000%+ growth
                    risks.append({
                        'type': 'extremely_unrealistic_growth',
                        'severity': 10,
                        'details': f"Growth rate of {growth_rate}% is extremely unrealistic",
                        'impact': 'high'
                    })
                elif growth_rate > 500:  # 500%+ growth
                    risks.append({
                        'type': 'unrealistic_growth',
                        'severity': 8,
                        'details': f"Growth rate of {growth_rate}% may be unrealistic for sustained periods",
                        'impact': 'high'
                    })
                elif growth_rate < 0:  # Negative growth
                    risks.append({
                        'type': 'negative_growth',
                        'severity': 7,
                        'details': f"Negative growth rate of {growth_rate}% indicates declining business",
                        'impact': 'high'
                    })
            
            # Burn rate and runway analysis
            burn_rate = self._safe_numeric_get(financials, 'burn_rate')
            funding_raised = self._safe_numeric_get(financials, 'funding_raised')
            
            if burn_rate is not None and burn_rate > 0 and funding_raised is not None:
                runway_months = funding_raised / burn_rate
                
                if runway_months < 6:
                    risks.append({
                        'type': 'critical_runway',
                        'severity': 10,
                        'details': f"Critical: Only {runway_months:.1f} months of runway remaining",
                        'impact': 'critical'
                    })
                elif runway_months < 12:
                    risks.append({
                        'type': 'short_runway',
                        'severity': 8,
                        'details': f"Short runway: {runway_months:.1f} months remaining",
                        'impact': 'high'
                    })
                elif runway_months < 18:
                    risks.append({
                        'type': 'moderate_runway',
                        'severity': 5,
                        'details': f"Moderate runway: {runway_months:.1f} months remaining",
                        'impact': 'medium'
                    })
            
            # Revenue vs burn rate mismatch
            if revenue is not None and burn_rate is not None and revenue > 0:
                revenue_coverage = (revenue * 12) / burn_rate if burn_rate > 0 else float('inf')
                if revenue_coverage < 0.3:  # Revenue covers less than 30% of burn
                    risks.append({
                        'type': 'low_revenue_coverage',
                        'severity': 7,
                        'details': f"Annual revenue only covers {revenue_coverage*100:.1f}% of burn rate",
                        'impact': 'high'
                    })
            
            # Funding seeking vs burn rate
            funding_seeking = self._safe_numeric_get(financials, 'funding_seeking')
            if funding_seeking is not None and burn_rate is not None and burn_rate > 0:
                potential_runway = funding_seeking / burn_rate
                if potential_runway < 18:
                    risks.append({
                        'type': 'insufficient_funding_target',
                        'severity': 6,
                        'details': f"Funding target would only provide {potential_runway:.1f} months runway",
                        'impact': 'medium'
                    })
            
            # Missing financial data risks
            if not any([revenue, burn_rate, funding_raised, growth_rate]):
                risks.append({
                    'type': 'missing_financial_data',
                    'severity': 6,
                    'details': "Critical financial metrics are missing or unclear",
                    'impact': 'medium'
                })
        
        except Exception as e:
            logger.error(f"Financial risk analysis error: {e}")
            risks.append({
                'type': 'financial_analysis_error',
                'severity': 5,
                'details': f"Could not complete financial risk analysis: {str(e)}",
                'impact': 'medium'
            })
        
        return risks

    async def analyze_market_risks(self, data: Dict) -> List[Dict]:
        """Evaluate market-related risks"""
        
        risks = []
        
        try:
            # Get market data with safe access
            market = data.get('market', {}) or data.get('synthesized_data', {}).get('market', {})
            
            # Market size validation
            market_size = self._safe_numeric_get(market, 'size')
            if market_size is not None:
                if market_size > 1e12:  # $1T+
                    risks.append({
                        'type': 'extremely_inflated_market',
                        'severity': 8,
                        'details': f"Market size of ${market_size/1e9:.0f}B appears extremely inflated",
                        'impact': 'high'
                    })
                elif market_size > 500e9:  # $500B+
                    risks.append({
                        'type': 'inflated_market_size',
                        'severity': 6,
                        'details': f"Market size of ${market_size/1e9:.0f}B may be inflated or too broad",
                        'impact': 'medium'
                    })
                elif market_size < 1e9:  # Less than $1B
                    risks.append({
                        'type': 'small_market_size',
                        'severity': 5,
                        'details': f"Market size of ${market_size/1e6:.0f}M may limit growth potential",
                        'impact': 'medium'
                    })
            
            # Competition analysis
            competitors = market.get('competitors', [])
            if isinstance(competitors, list):
                if len(competitors) == 0:
                    risks.append({
                        'type': 'no_competition_identified',
                        'severity': 6,
                        'details': "No competitors identified - may indicate poor market research or unrealistic assumptions",
                        'impact': 'medium'
                    })
                elif len(competitors) > 20:
                    risks.append({
                        'type': 'highly_competitive_market',
                        'severity': 7,
                        'details': f"Market has {len(competitors)} identified competitors - highly competitive space",
                        'impact': 'high'
                    })
            
            # Target market analysis
            target = market.get('target', '')
            if not target or len(target.strip()) < 20:
                risks.append({
                    'type': 'unclear_target_market',
                    'severity': 5,
                    'details': "Target market definition is unclear or too broad",
                    'impact': 'medium'
                })
            
        except Exception as e:
            logger.error(f"Market risk analysis error: {e}")
            risks.append({
                'type': 'market_analysis_error',
                'severity': 5,
                'details': f"Could not complete market risk analysis: {str(e)}",
                'impact': 'medium'
            })
        
        return risks

    async def analyze_team_risks(self, data: Dict) -> List[Dict]:
        """Analyze team-related risks"""
        
        risks = []
        
        try:
            # Get team data with safe access
            team = data.get('team', {}) or data.get('synthesized_data', {}).get('team', {})
            stage = data.get('stage', '') or data.get('synthesized_data', {}).get('stage', '')
            
            # Team size analysis
            team_size = self._safe_numeric_get(team, 'size')
            stage_lower = stage.lower() if stage else ''
            
            if team_size is not None:
                if 'series_a' in stage_lower and team_size < 5:
                    risks.append({
                        'type': 'small_team_for_stage',
                        'severity': 7,
                        'details': f"Team size of {team_size} is small for Series A stage",
                        'impact': 'high'
                    })
                elif 'series_b' in stage_lower and team_size < 10:
                    risks.append({
                        'type': 'small_team_for_stage',
                        'severity': 6,
                        'details': f"Team size of {team_size} may be small for Series B stage",
                        'impact': 'medium'
                    })
                elif team_size < 2:
                    risks.append({
                        'type': 'insufficient_team_size',
                        'severity': 8,
                        'details': f"Team size of {team_size} is insufficient for startup execution",
                        'impact': 'high'
                    })
                elif team_size > 200:
                    risks.append({
                        'type': 'oversized_team',
                        'severity': 5,
                        'details': f"Large team size of {team_size} may indicate inefficient operations",
                        'impact': 'medium'
                    })
            
            # Founder analysis
            founders = team.get('founders', [])
            if isinstance(founders, list):
                if len(founders) == 0:
                    risks.append({
                        'type': 'no_founders_identified',
                        'severity': 9,
                        'details': "No founders identified in team information",
                        'impact': 'critical'
                    })
                elif len(founders) == 1:
                    risks.append({
                        'type': 'single_founder_risk',
                        'severity': 6,
                        'details': "Single founder structure increases execution and key person risk",
                        'impact': 'medium'
                    })
                elif len(founders) > 4:
                    risks.append({
                        'type': 'too_many_founders',
                        'severity': 5,
                        'details': f"{len(founders)} founders may lead to decision-making conflicts",
                        'impact': 'medium'
                    })
            
            # Key hires analysis
            key_hires = team.get('key_hires', [])
            if isinstance(key_hires, list) and len(key_hires) == 0 and team_size and team_size > 10:
                risks.append({
                    'type': 'no_key_hires_identified',
                    'severity': 4,
                    'details': "No key hires identified despite team size - may indicate weak talent acquisition",
                    'impact': 'low'
                })
            
        except Exception as e:
            logger.error(f"Team risk analysis error: {e}")
            risks.append({
                'type': 'team_analysis_error',
                'severity': 5,
                'details': f"Could not complete team risk analysis: {str(e)}",
                'impact': 'medium'
            })
        
        return risks

    async def analyze_product_risks(self, data: Dict) -> List[Dict]:
        """Analyze product and technology risks"""
        
        risks = []
        
        try:
            # Get product data with safe access
            product = data.get('product', {}) or data.get('synthesized_data', {}).get('product', {})
            
            # Product differentiation analysis
            differentiation = product.get('differentiation', '')
            if not differentiation or len(differentiation.strip()) < 30:
                risks.append({
                    'type': 'unclear_differentiation',
                    'severity': 6,
                    'details': "Product differentiation is unclear or poorly defined",
                    'impact': 'medium'
                })
            
            # Product description analysis
            description = product.get('description', '')
            if not description or len(description.strip()) < 50:
                risks.append({
                    'type': 'vague_product_description',
                    'severity': 5,
                    'details': "Product description is vague or insufficient",
                    'impact': 'medium'
                })
            
            # Product stage analysis
            product_stage = product.get('stage', '').lower()
            company_stage = data.get('stage', '').lower()
            
            if 'concept' in product_stage or 'idea' in product_stage:
                if 'series_a' in company_stage:
                    risks.append({
                        'type': 'product_stage_mismatch',
                        'severity': 8,
                        'details': "Product still in concept stage but seeking Series A funding",
                        'impact': 'high'
                    })
            
            # Business model analysis
            business_model = product.get('business_model', '')
            if not business_model or len(business_model.strip()) < 20:
                risks.append({
                    'type': 'unclear_business_model',
                    'severity': 6,
                    'details': "Business model is unclear or not well defined",
                    'impact': 'medium'
                })
            
        except Exception as e:
            logger.error(f"Product risk analysis error: {e}")
            risks.append({
                'type': 'product_analysis_error',
                'severity': 5,
                'details': f"Could not complete product risk analysis: {str(e)}",
                'impact': 'medium'
            })
        
        return risks

    async def analyze_operational_risks(self, data: Dict) -> List[Dict]:
        """Analyze operational risks using AI and heuristics"""
        
        risks = []
        
        try:
            # Basic operational risk checks
            traction = data.get('traction', {}) or data.get('synthesized_data', {}).get('traction', {})
            
            # Customer vs user analysis
            customers = self._safe_numeric_get(traction, 'customers')
            users = self._safe_numeric_get(traction, 'users')
            
            if users is not None and customers is not None:
                if users > 0 and customers == 0:
                    risks.append({
                        'type': 'users_without_customers',
                        'severity': 6,
                        'details': f"Has {users} users but no paying customers - monetization challenge",
                        'impact': 'medium'
                    })
                elif users > 0 and customers > 0:
                    conversion_rate = customers / users
                    if conversion_rate < 0.01:  # Less than 1% conversion
                        risks.append({
                            'type': 'low_conversion_rate',
                            'severity': 7,
                            'details': f"Very low user-to-customer conversion rate ({conversion_rate*100:.2f}%)",
                            'impact': 'high'
                        })
            
            # Partnership analysis
            partnerships = traction.get('partnerships', [])
            if isinstance(partnerships, list) and len(partnerships) == 0:
                stage = data.get('stage', '').lower()
                if 'series_a' in stage or 'series_b' in stage:
                    risks.append({
                        'type': 'no_partnerships',
                        'severity': 4,
                        'details': "No partnerships identified for growth stage company",
                        'impact': 'low'
                    })
            
            # Advanced AI-powered operational risk analysis
            await self._ai_operational_risk_analysis(data, risks)
            
        except Exception as e:
            logger.error(f"Operational risk analysis error: {e}")
            risks.append({
                'type': 'operational_analysis_error',
                'severity': 5,
                'details': f"Could not complete operational risk analysis: {str(e)}",
                'impact': 'medium'
            })
        
        return risks

    async def _ai_operational_risk_analysis(self, data: Dict, risks: List[Dict]) -> None:
        """Use Gemini AI for advanced operational risk pattern detection"""
        
        try:
            # Prepare data for AI analysis (limit size)
            analysis_data = json.dumps(data, indent=2)[:4000]
            
            prompt = f"""
            Analyze this startup data for operational risks and inconsistencies. Focus on:
            
            1. Data inconsistencies between metrics
            2. Timeline mismatches
            3. Unusual patterns that suggest operational issues
            4. Missing critical operational information
            5. Unrealistic operational claims
            
            Startup data:
            {analysis_data}
            
            Return a JSON array of operational risks. Each risk should have:
            - type: short identifier for the risk
            - severity: number from 1-10
            - details: clear explanation of the risk
            - impact: 'low', 'medium', 'high', or 'critical'
            
            Example format:
            [
                {{
                    "type": "inconsistent_metrics",
                    "severity": 7,
                    "details": "User growth doesn't align with revenue growth patterns",
                    "impact": "high"
                }}
            ]
            
            Return only the JSON array, no other text.
            """
            
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            if response and response.text:
                # Extract JSON from response
                response_text = response.text.strip()
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    ai_risks = json.loads(json_str)
                    
                    # Validate and add AI-identified risks
                    for risk in ai_risks:
                        if isinstance(risk, dict) and all(k in risk for k in ['type', 'severity', 'details']):
                            # Ensure severity is within bounds
                            risk['severity'] = max(1, min(10, int(risk.get('severity', 5))))
                            if 'impact' not in risk:
                                risk['impact'] = 'medium'
                            risks.append(risk)
                    
                    logger.info(f"AI identified {len(ai_risks)} operational risks")
        
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse AI operational risk response: {e}")
        except Exception as e:
            logger.warning(f"AI operational risk analysis failed: {e}")
            # Don't add error to risks since this is supplementary analysis

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

    async def generate_risk_explanations(self, risks: Dict[str, List[Dict]], startup_data: Dict) -> List[str]:
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