# Pydantic models

# models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class WeightingConfig(BaseModel):
    profile_name: str = "custom"
    weights: Dict[str, float] = Field(
        default={
            "growth_potential": 0.25,
            "market_opportunity": 0.20,
            "team_quality": 0.20,
            "product_technology": 0.15,
            "financial_metrics": 0.10,
            "competitive_position": 0.10
        }
    )

class AnalysisRequest(BaseModel):
    storage_paths: List[str]
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    weighting_config: Optional[WeightingConfig] = None

class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    message: str
    progress: Optional[int] = 0

class ChatRequest(BaseModel):
    analysis_id: str
    question: str
    context: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    response: str
    suggested_questions: List[str]
    analysis_id: str


class DocumentUploadRequest(BaseModel):
    filename: str
    content_type: str