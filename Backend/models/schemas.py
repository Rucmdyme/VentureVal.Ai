
# models/schemas.py
from pydantic import BaseModel, Field, EmailStr, validator, root_validator
from typing import List, Optional, Dict, Any, Literal, Union
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

ALLOWED_STAGES = Literal["Idea", "MVP", "Revenue", "Scaling", "Seed", "Series A", "Series B"]

class EntrepreneurDetails(BaseModel):
    """Model for fields specific to the 'Entrepreneur' role."""
    role: Literal["Entrepreneur"] = "Entrepreneur"
    startup_name: Optional[str] = Field(None, description="Startup Name")
    stage: Optional[ALLOWED_STAGES] = Field(None, description="Current stage of the startup")
    sector: Optional[str] = Field(None, description="e.g., FinTech, HealthTech, AI/ML")


class InvestorDetails(BaseModel):
    """Model for fields specific to the 'Investor' role."""
    role: Literal["Investor"] = "Investor"
    investment_stages: Optional[List[ALLOWED_STAGES]] = Field(None, description="Investment Stage Preference")    
    sectors_of_interest: Optional[List[str]] = Field(None, description="e.g., FinTech, HealthTech, AI/ML")


class AdvisorDetails(BaseModel):
    """Model for fields specific to the 'Advisor' role."""
    role: Literal["Advisor"] = "Advisor"
    organization: Optional[str] = Field(None, description="Organization")
    profile: Optional[str] = Field(None, description="Role title within the organization")
    focus_area: Optional[List[str]] = Field(None, description="e.g., Due diligence, Management, Deal Sourcing")


RoleSpecificDetails = Union[EntrepreneurDetails, InvestorDetails, AdvisorDetails]

class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    location: Optional[str] = None
    role_details: Optional[RoleSpecificDetails] = Field(
        None,
        description="Role-specific details required for certain user types.",
        discriminator='role'
    )
    @root_validator(pre=True)
    def handle_empty_role_details(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        role_details = values.get('role_details')
        if not role_details:
            values['role_details'] = None
        return values

    # @validator('password')
    # def validate_password(cls, v):
    #     if len(v) < 8:
    #         raise ValueError('Password must be at least 8 characters long')
    #     if not re.search(r'[A-Z]', v):
    #         raise ValueError('Password must contain at least one uppercase letter')
    #     if not re.search(r'[a-z]', v):
    #         raise ValueError('Password must contain at least one lowercase letter')
    #     if not re.search(r'\d', v):
    #         raise ValueError('Password must contain at least one digit')
    #     return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ResendVerificationLink(BaseModel):
    token: str
    