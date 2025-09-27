
# models/schemas.py
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from enum import Enum
import re

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
    idtoken: Optional[str] = None
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
    idtoken: Optional[str] = None
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

# User schemas for user management
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    role: str
    location: Optional[str] = None
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['admin', 'founder', 'investor', 'analyst']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ResendVerificationLink(BaseModel):
    token: str
    