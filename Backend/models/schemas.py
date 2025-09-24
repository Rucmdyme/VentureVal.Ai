# Pydantic models

# models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class WeightingConfig(BaseModel):
    profile_name: str = "Default (Custom)"
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
    chat_history: Optional[List[Dict]] = []

class ChatResponse(BaseModel):
    response: str
    suggested_questions: List[str]
    analysis_id: str


class FileType(str, Enum):
    PITCH_DECK = "pitch_deck"
    CALL_TRANSCRIPT = "call_transcript" 
    FOUNDER_UPDATE = "founder_update"
    EMAIL_COMMUNICATION = "email_communication"

class DocumentUploadRequest(BaseModel):
    filename: str
    file_type: FileType = Field(..., description="Type of document being uploaded")