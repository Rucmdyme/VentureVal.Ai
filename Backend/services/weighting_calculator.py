# Score calculation

# services/weighting_calculator.py
from typing import Dict, List
from utils.helpers import db_insert, db_update
from constants import Collections


class WeightingCalculator:
    def __init__(self):
        self.default_weights = {
            'growth_potential': 0.25,
            'market_opportunity': 0.20,
            'team_quality': 0.20,
            'product_technology': 0.15,
            'financial_metrics': 0.10,
            'competitive_position': 0.10
        }

    async def calculate_weighted_score(self, analysis_id: str, startup_data: Dict, risk_assessment: Dict, 
                                     benchmark_results: Dict, weighting_config: Dict, operation_type: str = "insert") -> Dict:
        """Apply custom weightings to generate final scores"""
        
        weights = weighting_config.get('weights', self.default_weights)
        
        # Validate weights sum to 1.0
        if abs(sum(weights.values()) - 1.0) > 0.01:
            raise ValueError("Weights must sum to 100%")
        
        # Calculate dimension scores (1-10 scale)
        dimension_scores = {
            'growth_potential': self.calculate_growth_score(startup_data, benchmark_results),
            'market_opportunity': self.calculate_market_score(startup_data),
            'team_quality': self.calculate_team_score(startup_data),
            'product_technology': self.calculate_product_score(startup_data),
            'financial_metrics': self.calculate_financial_score(startup_data),
            'competitive_position': self.calculate_competitive_score(startup_data)
        }
        
        # Apply risk penalty
        risk_penalty = (10 - risk_assessment.get('overall_risk_score', 5)) / 10
        
        # Calculate weighted score
        weighted_score = 0
        for dimension, score in dimension_scores.items():
            weighted_contribution = score * weights[dimension]
            weighted_score += weighted_contribution
        
        # Generate recommendation
        recommendation = self.generate_weighted_recommendation(
            weighted_score, dimension_scores, weights, risk_assessment
        )
        data = {
            'overall_score': round(weighted_score, 2),
            'dimension_scores': dimension_scores,
            'weights_applied': weights,
            'recommendation': recommendation,
            'risk_penalty': risk_penalty
        }
        if operation_type == "insert":
            await db_insert(analysis_id, Collections.WEIGHTED_SCORES, data)
        else:
            await db_update(analysis_id, Collections.WEIGHTED_SCORES, data)
        return data

    def calculate_growth_score(self, data: Dict, benchmarks: Dict) -> float:
        """Calculate growth potential score"""
        
        growth_rate = (data.get('financials') or {}).get('growth_rate') or 0
        
        if growth_rate == 0:
            return 3.0  # Below average if no growth data
        
        # Compare to sector benchmarks
        sector_growth = (benchmarks.get('percentiles') or {}).get('growth_rate') or {}
        percentile = sector_growth.get('percentile') or 50
        
        # Convert percentile to 1-10 score
        if percentile >= 90:
            return 9.5
        elif percentile >= 75:
            return 8.0
        elif percentile >= 50:
            return 6.5
        elif percentile >= 25:
            return 4.5
        else:
            return 2.5

    def calculate_market_score(self, data: Dict) -> float:
        """Calculate market opportunity score"""
        
        market = data.get('market') or {}
        market_size = market.get('size') or 0
        target = market.get('target_segment') or ''
        competitors = market.get('competitors') or []
        
        score = 5.0  # Base score
        
        # Market size impact
        if market_size > 10e9:  # $10B+
            score += 2.0
        elif market_size > 1e9:  # $1B+
            score += 1.0
        
        # Target market clarity
        if len(target) > 50:  # Well-defined target
            score += 1.0
        
        # Competition level
        if 1 <= len(competitors) <= 5:  # Healthy competition
            score += 1.0
        elif len(competitors) > 10:  # Overcrowded
            score -= 1.0
        
        return min(10.0, max(1.0, score))

    def calculate_team_score(self, data: Dict) -> float:
        """Calculate team quality score"""
        
        team = data.get('team') or {}
        team_size = team.get('size') or 0
        founders = team.get('founders') or []
        
        score = 5.0  # Base score
        
        # Team size appropriateness
        stage = (data.get('stage') or '').lower()
        if stage == 'seed' and 3 <= team_size <= 10:
            score += 1.5
        elif stage == 'series_a' and 8 <= team_size <= 25:
            score += 1.5
        
        # Founder count
        if len(founders) == 2:  # Ideal founder count
            score += 1.5
        elif len(founders) == 3:
            score += 1.0
        elif len(founders) == 1:
            score -= 1.0
        
        return min(10.0, max(1.0, score))

    def calculate_product_score(self, data: Dict) -> float:
        product = data.get('product') or {}
        description = product.get('description') or ''
        competitive_advantage = product.get('competitive_advantage') or ''
        stage = product.get('stage') or ''
        
        score = 5.0  # Base score
        
        # Product description quality
        if len(description) > 100:
            score += 1.0
        
        # competitive_advantage clarity
        if len(competitive_advantage) > 50:
            score += 2.0
        elif len(competitive_advantage) > 20:
            score += 1.0
        
        # Development stage
        if 'mvp' in stage.lower() or 'beta' in stage.lower():
            score += 1.0
        elif 'production' in stage.lower():
            score += 2.0
    
        return min(10.0, max(1.0, score))

    def calculate_financial_score(self, data: Dict) -> float:
        """Calculate financial metrics score"""
        
        financials = data.get('financials') or {}
        revenue = financials.get('revenue') or 0
        growth_rate = financials.get('growth_rate') or 0
        
        score = 5.0  # Base score
        
        # Revenue presence
        if revenue > 1000000:  # $1M+ revenue
            score += 2.0
        elif revenue > 100000:  # $100K+ revenue
            score += 1.0
        
        # Growth rate
        if growth_rate > 100:  # 100%+ growth
            score += 2.0
        elif growth_rate > 50:  # 50%+ growth
            score += 1.0
        
        return min(10.0, max(1.0, score))

    def calculate_competitive_score(self, data: Dict) -> float:
        """Calculate competitive position score"""
        
        market = data.get('market') or {}
        competitors = market.get('competitors') or []
        competitive_advantage = (data.get('product') or {}).get('competitive_advantage') or ''
        
        score = 5.0  # Base score
        
        # Competitive landscape
        if 2 <= len(competitors) <= 5:  # Good competitive landscape
            score += 1.5
        elif len(competitors) > 10:  # Highly competitive
            score -= 1.0
        elif len(competitors) == 0:  # Unclear market
            score -= 2.0

        # Competitive advantage strength
        if len(competitive_advantage) > 100:  # Strong competitive advantage
            score += 2.0
        elif len(competitive_advantage) > 50:
            score += 1.0
        
        return min(10.0, max(1.0, score))

    def generate_weighted_recommendation(self, score: float, dimensions: Dict, 
                                    weights: Dict, risk_assessment: Dict) -> Dict:
        """Generate recommendation explaining weighting impact"""
        
        # Determine recommendation tier
        if score >= 7.5:
            tier = "PURSUE"
            confidence = 85
        elif score >= 6.0:
            tier = "CONSIDER"
            confidence = 65
        else:
            tier = "PASS"
            confidence = 45
        
        # Find highest-weighted dimensions
        top_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:2]
        
        # Generate explanation
        explanation = f"""
        Recommendation: {tier} (Score: {score:.1f}/10, Confidence: {confidence}%)
        
        Key factors based on your investment priorities:
        • {top_weights[0][0].replace('_', ' ').title()}: {weights[top_weights[0][0]]*100:.0f}% weight → {dimensions[top_weights[0][0]]:.1f}/10 score
        • {top_weights[1][0].replace('_', ' ').title()}: {weights[top_weights[1][0]]*100:.0f}% weight → {dimensions[top_weights[1][0]]:.1f}/10 score
        
        Risk Impact: {risk_assessment.get('overall_risk_score', 5):.1f}/10 risk score applied as penalty
        
        This startup {tier.lower()}s your investment criteria based on weighted analysis.
        """
        
        return {
            'tier': tier,
            'explanation': explanation.strip(),
            'confidence': confidence,
            'key_strengths': self.identify_strengths(dimensions, weights),
            'key_concerns': risk_assessment.get('risk_explanations', [])[:3]
        }

    def identify_strengths(self, dimensions: Dict, weights: Dict) -> List[str]:
        """Identify key strengths based on weighted scores"""
        
        # Weight each dimension score by its importance
        weighted_dimensions = {
            dim: score * weights.get(dim, 0.1) 
            for dim, score in dimensions.items()
        }

        # Get top 3 weighted strengths
        top_strengths = sorted(weighted_dimensions.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return [
            f"Strong {dim.replace('_', ' ')}: {dimensions[dim]:.1f}/10"
            for dim, _ in top_strengths if dimensions[dim] >= 7.0
        ]