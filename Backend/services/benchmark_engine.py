# services/benchmark_engine.py
import json
import asyncio
from typing import Dict, Optional
from datetime import datetime
from google import genai
from utils.ai_client import configure_gemini
import logging
from settings import PROJECT_ID, GCP_REGION

logger = logging.getLogger(__name__)

class BenchmarkEngine:
    def __init__(self):
        """Initialize with Gemini configuration"""
        self.gemini_available = configure_gemini()
        if self.gemini_available:
            self.model = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=GCP_REGION
            )
            # self.model = genai.GenerativeModel('gemini-pro')
            logger.info("BenchmarkEngine initialized with Gemini AI")
        else:
            logger.warning("BenchmarkEngine falling back to static benchmarks")
            self.model = None
    
    async def get_sector_benchmarks(self, sector: str, geography: str = 'US', stage: str = None) -> Dict:
        """Get benchmark data using Gemini AI or fallback to static data"""
        
        if not self.gemini_available or not self.model:
            logger.info("Using fallback benchmarks")
            return self.get_default_benchmarks()
        
        try:
            stage_info = f" for {stage} stage companies" if stage else ""
            
            prompt = f"""
            You are a senior investment analyst with access to comprehensive market data. Generate realistic and accurate startup benchmark percentiles for the {sector} sector in {geography}{stage_info} based on current 2024-2025 market conditions.

            SECTOR CONTEXT: {sector}
            GEOGRAPHY: {geography}
            STAGE: {stage if stage else 'All stages'}

            BENCHMARKING REQUIREMENTS:
            1. Use actual market data patterns for {sector} companies
            2. Account for current economic conditions and funding environment
            3. Reflect stage-appropriate metrics for {stage if stage else 'various stages'}
            4. Consider geographic market differences for {geography}
            5. Include sector-specific business model characteristics

            SECTOR-SPECIFIC CONSIDERATIONS FOR {sector}:
            - Typical business models and revenue streams
            - Standard unit economics and growth patterns  
            - Market maturity and competitive dynamics
            - Capital requirements and burn rate patterns
            - Team composition and scaling requirements
            - Valuation multiples and investor expectations

            STAGE-SPECIFIC ADJUSTMENTS{f' FOR {stage.upper()}' if stage else ''}:
            - Appropriate revenue ranges and growth expectations
            - Team size and organizational structure
            - Funding amounts and valuation ranges
            - Burn rate and runway expectations
            - Traction and customer metrics

            Return ONLY valid JSON in this exact format with realistic numbers:
            {{
                "revenue_multiples": {{
                    "p10": "10th percentile annual revenue in multiples",
                    "p25": "25th percentile annual revenue in multiples", 
                    "p50": "50th percentile (median) annual revenue in multiples",
                    "p75": "75th percentile annual revenue in multiples",
                    "p90": "90th percentile annual revenue in multiples"
                }},
                "growth_rates": {{
                    "p10": "10th percentile annual revenue growth rate percentage",
                    "p25": "25th percentile annual revenue growth rate percentage",
                    "p50": "50th percentile annual revenue growth rate percentage", 
                    "p75": "75th percentile annual revenue growth rate percentage",
                    "p90": "90th percentile annual revenue growth rate percentage"
                }},
                "team_sizes": {{
                    "p10": "10th percentile total team size (full-time employees)",
                    "p25": "25th percentile total team size",
                    "p50": "50th percentile total team size",
                    "p75": "75th percentile total team size", 
                    "p90": "90th percentile total team size"
                }},
                "burn_rates_monthly": {{
                    "p10": "10th percentile monthly cash burn in USD",
                    "p25": "25th percentile monthly cash burn in USD",
                    "p50": "50th percentile monthly cash burn in USD",
                    "p75": "75th percentile monthly cash burn in USD",
                    "p90": "90th percentile monthly cash burn in USD"
                }},
                "runway_months": {{
                    "p10": "10th percentile runway in months",
                    "p25": "25th percentile runway in months", 
                    "p50": "50th percentile runway in months",
                    "p75": "75th percentile runway in months",
                    "p90": "90th percentile runway in months"
                }},
                "valuation_millions": {{
                    "p10": "10th percentile company valuation in millions USD",
                    "p25": "25th percentile company valuation in millions USD",
                    "p50": "50th percentile company valuation in millions USD",
                    "p75": "75th percentile company valuation in millions USD", 
                    "p90": "90th percentile company valuation in millions USD"
                }}
            }}

            CRITICAL REQUIREMENTS:
            1. All numbers must be realistic for {sector} companies in {geography}
            2. Percentiles must be properly ordered (p10 < p25 < p50 < p75 < p90)
            3. Consider current market conditions (2024-2025 funding environment)
            4. Account for sector-specific business model characteristics
            5. Reflect stage-appropriate expectations and metrics
            6. Use whole numbers for counts, appropriate precision for financial metrics
            7. Ensure burn rates align with team sizes and stage expectations
            8. Valuations should reflect current market multiples for the sector
            9. Growth rates should be realistic and sustainable
            10. Unit economics should reflect healthy vs struggling companies across percentiles
            """
            
            response = await asyncio.to_thread(self.model.models.generate_content, model="gemini-2.5-flash", contents = [prompt])
            response_text = response.text.strip()
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                benchmarks = json.loads(json_str)
                logger.info(f"Generated Gemini benchmarks for {sector}")
                return benchmarks
            else:
                logger.warning("Failed to parse Gemini response, using fallback")
                return self.get_default_benchmarks()
                
        except Exception as e:
            logger.error(f"Error getting benchmarks from Gemini: {e}")
            return self.get_default_benchmarks()
    
    async def calculate_percentiles(self, startup_data: Dict, sector: str) -> Dict:
        """Calculate startup's percentile rankings - main method called by process_analysis"""
        
        # Extract stage and geography from startup data
        stage = startup_data.get('stage', 'series_a')
        geography = startup_data.get('geography', 'US')
        
        # Get benchmarks (either from Gemini or fallback)
        benchmarks = await self.get_sector_benchmarks(sector, geography, stage)
        
        percentiles = {}
        
        # Map startup data fields to benchmark categories
        metrics_to_analyze = [
            ('growth_rate', 'financials.growth_rate', 'growth_rates'),
            ('team_size', 'team.size', 'team_sizes'),
            ('burn_rate', 'financials.burn_rate', 'burn_rates_monthly'),
            ('runway', 'financials.runway_months', 'runway_months'),
            ('valuation', 'financials.valuation', 'valuation_millions'),
            ('revenue', 'financials.revenue', 'revenue_multiples')
        ]
        
        for metric_name, data_path, benchmark_key in metrics_to_analyze:
            value = self._extract_nested_value(startup_data, data_path)
            
            if value is not None and benchmark_key in benchmarks:
                percentile_data = self.calculate_single_percentile(
                    value, 
                    benchmarks[benchmark_key],
                    metric_name
                )
                percentiles[metric_name] = percentile_data
        
        # Calculate overall performance score
        overall_score = self._calculate_overall_score(percentiles)
        
        # Generate insights if Gemini is available
        insights = await self._generate_insights(startup_data, percentiles, sector) if self.gemini_available else []
        
        return {
            'percentiles': percentiles,
            'overall_score': overall_score,
            'sector_benchmarks': benchmarks,
            'insights': insights,
            'analysis_date': datetime.now().isoformat(),
            'data_source': 'gemini_ai' if self.gemini_available else 'static_fallback'
        }
    
    def calculate_single_percentile(self, value: float, benchmark_distribution: Dict, metric_name: str) -> Dict:
        """Calculate percentile for a single metric"""
        
        try:
            p10 = benchmark_distribution.get('p10') or 0
            p25 = benchmark_distribution.get('p25') or 0
            p50 = benchmark_distribution.get('p50') or 0
            p75 = benchmark_distribution.get('p75') or 0
            p90 = benchmark_distribution.get('p90') or 0
            
            # Calculate percentile
            if value <= p10:
                percentile = 5
            elif value <= p25:
                percentile = 17.5
            elif value <= p50:
                percentile = 37.5
            elif value <= p75:
                percentile = 62.5
            elif value <= p90:
                percentile = 82.5
            else:
                percentile = 95
            
            # Special handling for metrics where lower is better (burn rate)
            if metric_name in ['burn_rate']:
                percentile = 100 - percentile
            
            return {
                'value': value,
                'percentile': percentile,
                'interpretation': self.interpret_percentile(percentile),
                'benchmark_median': p50,
                'benchmark_top_quartile': p25,
                'relative_performance': self._get_relative_performance(value, p50, metric_name)
            }
            
        except Exception as e:
            logger.error(f"Error calculating percentile for {metric_name}: {e}")
            return {
                'value': value,
                'percentile': 50,
                'interpretation': "Unable to calculate - data issue",
                'error': str(e)
            }
    
    async def _generate_insights(self, startup_data: Dict, percentiles: Dict, sector: str) -> list:
        """Generate AI insights based on performance"""
        
        if not self.model:
            return []
        
        try:
            # Find underperforming metrics
            weak_areas = [
                metric for metric, data in percentiles.items() 
                if data.get('percentile', 50) < 40
            ]
            
            strong_areas = [
                metric for metric, data in percentiles.items() 
                if data.get('percentile', 50) >= 75
            ]
            
            prompt = f"""
            You are a senior investment analyst providing detailed benchmark analysis for a {sector} startup. Generate specific, actionable insights based on their performance relative to sector peers.

            COMPANY PROFILE:
            - Sector: {sector}
            - Stage: {startup_data.get('stage', 'unknown')}
            - Geography: {startup_data.get('geography', 'unknown')}

            PERFORMANCE ANALYSIS:
            - Strong Performance Areas (75th+ percentile): {strong_areas}
            - Underperforming Areas (below 40th percentile): {weak_areas}
            - Company Revenue: {startup_data.get('financials', {}).get('revenue', 'Not disclosed')}
            - Team Size: {startup_data.get('team', {}).get('size', 'Not disclosed')}
            - Growth Rate: {startup_data.get('financials', {}).get('growth_rate', 'Not disclosed')}%

            INSIGHT GENERATION REQUIREMENTS:
            1. Compare performance to {sector} sector benchmarks specifically
            2. Consider stage-appropriate expectations for {startup_data.get('stage', 'unknown')} companies
            3. Identify competitive advantages from strong performance areas
            4. Highlight critical improvement areas that could impact valuation
            5. Provide sector-specific context and implications
            6. Consider market timing and competitive dynamics
            7. Address investor concerns and opportunities

            Generate 4-5 comprehensive insights covering:
            - Competitive positioning analysis
            - Growth trajectory assessment  
            - Operational efficiency evaluation
            - Market opportunity alignment
            - Investment risk/opportunity summary

            Return ONLY a JSON array of detailed insights:
            [
                "Specific insight about competitive positioning with quantitative context and sector comparison",
                "Detailed analysis of growth performance with benchmarking context and implications", 
                "Operational efficiency assessment with specific metrics and improvement recommendations",
                "Market opportunity evaluation with sector trends and positioning analysis",
                "Investment summary with key strengths, concerns, and strategic recommendations"
            ]

            Each insight should be:
            - Specific to the {sector} sector and {startup_data.get('stage', 'unknown')} stage
            - Quantitative where possible with percentile references
            - Actionable with clear implications for management and investors
            - Forward-looking with market context and competitive dynamics
            - 2-3 sentences with concrete details and recommendations
            """
            
            response = await asyncio.to_thread(self.model.models.generate_content, model="gemini-2.5-flash",contents = [prompt])
            response_text = response.text.strip()
            
            # Extract JSON array
            array_start = response_text.find('[')
            array_end = response_text.rfind(']') + 1
            
            if array_start != -1 and array_end > array_start:
                json_str = response_text[array_start:array_end]
                insights = json.loads(json_str)
                return insights[:4]  # Limit to 4 insights
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return []
    
    def _extract_nested_value(self, data: Dict, path: str) -> Optional[float]:
        """Extract value from nested dictionary using dot notation"""
        
        try:
            keys = path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            # Convert to float if possible
            if value is not None:
                return float(value)
                
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _calculate_overall_score(self, percentiles: Dict) -> Dict:
        """Calculate weighted overall performance score"""
        
        if not percentiles:
            return {'score': 0, 'grade': 'N/A', 'metrics_count': 0}
        
        # Weights for different metrics
        weights = {
            'growth_rate': 0.25,
            'team_size': 0.15,
            'burn_rate': 0.20,
            'runway': 0.15,
            'valuation': 0.15,
            'revenue': 0.10
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for metric, data in percentiles.items():
            if metric in weights and 'percentile' in data:
                weight = weights[metric]
                weighted_sum += data['percentile'] * weight
                total_weight += weight
        
        if total_weight == 0:
            return {'score': 0, 'grade': 'N/A', 'metrics_count': 0}
        
        final_score = weighted_sum / total_weight
        
        # Assign letter grades
        if final_score >= 80:
            grade = 'A'
        elif final_score >= 65:
            grade = 'B'  
        elif final_score >= 50:
            grade = 'C'
        elif final_score >= 35:
            grade = 'D'
        else:
            grade = 'F'
        
        return {
            'score': round(final_score, 1),
            'grade': grade,
            'metrics_count': len(percentiles)
        }
    
    def _get_relative_performance(self, value: float, median: float, metric_name: str) -> str:
        """Get relative performance description"""
        
        if median == 0:
            return "Unable to compare"
        
        ratio = value / median
        
        # For burn rate, lower is better
        if metric_name == 'burn_rate':
            if ratio <= 0.7:
                return "Significantly above median"
            elif ratio <= 0.9:
                return "Above median"
            elif ratio <= 1.1:
                return "Close to median"
            else:
                return "Below median"
        else:
            # For other metrics, higher is generally better
            if ratio >= 1.5:
                return "Significantly above median"
            elif ratio >= 1.2:
                return "Above median"
            elif ratio >= 0.8:
                return "Close to median"
            else:
                return "Below median"
    
    def interpret_percentile(self, percentile: float) -> str:
        """Interpret percentile score"""
        if percentile >= 80:
            return "Excellent - Top 20% performance"
        elif percentile >= 60:
            return "Above Average - Top 40% performance"
        elif percentile >= 40:
            return "Average - Typical performance"
        elif percentile >= 20:
            return "Below Average - Bottom 40% performance"
        else:
            return "Poor - Bottom 20% performance"
    
    def get_default_benchmarks(self) -> Dict:
        """Enhanced fallback benchmarks"""
        return {
            'revenue_multiples': {
                'p10': 1, 'p25': 3, 'p50': 6, 'p75': 12, 'p90': 25
            },
            'growth_rates': {
                'p10': 20, 'p25': 50, 'p50': 100, 'p75': 200, 'p90': 400
            },
            'team_sizes': {
                'p10': 3, 'p25': 8, 'p50': 15, 'p75': 30, 'p90': 60
            },
            'burn_rates_monthly': {
                'p10': 15000, 'p25': 35000, 'p50': 75000, 'p75': 150000, 'p90': 300000
            },
            'runway_months': {
                'p10': 6, 'p25': 12, 'p50': 18, 'p75': 24, 'p90': 36
            },
            'valuation_millions': {
                'p10': 2, 'p25': 8, 'p50': 20, 'p75': 50, 'p90': 150
            }
        }