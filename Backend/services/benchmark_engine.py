# services/benchmark_engine.py
import json
import asyncio
from typing import Dict, Optional
from datetime import datetime
from google import genai
from utils.ai_client import configure_gemini
import logging

logger = logging.getLogger(__name__)

class BenchmarkEngine:
    def __init__(self):
        """Initialize with Gemini configuration"""
        self.gemini_available = configure_gemini()
        if self.gemini_available:
            self.model = genai.Client(
                vertexai=True,
                project="ventureval-ef705",
                location="us-central1"
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
            Generate realistic startup benchmark data for the {sector} sector in {geography}{stage_info}.
            
            Return ONLY valid JSON in this exact format:
            {{
                "revenue_multiples": {{
                    "p10": <number>,
                    "p25": <number>,
                    "p50": <number>,
                    "p75": <number>,
                    "p90": <number>
                }},
                "growth_rates": {{
                    "p10": <number>,
                    "p25": <number>,
                    "p50": <number>,
                    "p75": <number>,
                    "p90": <number>
                }},
                "team_sizes": {{
                    "p10": <number>,
                    "p25": <number>,
                    "p50": <number>,
                    "p75": <number>,
                    "p90": <number>
                }},
                "burn_rates_monthly": {{
                    "p10": <number>,
                    "p25": <number>,
                    "p50": <number>,
                    "p75": <number>,
                    "p90": <number>
                }},
                "runway_months": {{
                    "p10": <number>,
                    "p25": <number>,
                    "p50": <number>,
                    "p75": <number>,
                    "p90": <number>
                }},
                "valuation_millions": {{
                    "p10": <number>,
                    "p25": <number>,
                    "p50": <number>,
                    "p75": <number>,
                    "p90": <number>
                }}
            }}
            
            Base this on current 2024-2025 market data for {sector} companies. 
            Growth rates should be annual percentages.
            Burn rates in USD per month.
            Team sizes as employee count.
            Valuations in millions USD.
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
            p10 = benchmark_distribution.get('p10', 0)
            p25 = benchmark_distribution.get('p25', 0)
            p50 = benchmark_distribution.get('p50', 0)
            p75 = benchmark_distribution.get('p75', 0)
            p90 = benchmark_distribution.get('p90', 0)
            
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
                'benchmark_top_quartile': p75,
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
            Analyze this {sector} startup's benchmark performance and provide 3-4 specific insights:
            
            Strong areas (75th+ percentile): {strong_areas}
            Weak areas (below 40th percentile): {weak_areas}
            
            Company stage: {startup_data.get('stage', 'unknown')}
            
            Return ONLY a JSON array of insights:
            ["insight 1", "insight 2", "insight 3"]
            
            Make insights specific, actionable, and relevant to the sector and stage.
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
                return "Significantly better than median"
            elif ratio <= 0.9:
                return "Better than median"
            elif ratio <= 1.1:
                return "Close to median"
            else:
                return "Higher than median"
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