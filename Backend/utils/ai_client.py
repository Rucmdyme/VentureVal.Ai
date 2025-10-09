# Google AI clients

# utils/ai_client.py
from google import genai
from functools import wraps
from datetime import datetime
from fastapi import HTTPException
import logging
from settings import PROJECT_ID, GCP_REGION


logger = logging.getLogger(__name__)

# Global clients
cost_monitor = None
_gemini_configured = False

_gemini_client = None

def configure_gemini():
    """Centralized Gemini configuration with singleton pattern"""
    global _gemini_configured, _gemini_client
    
    if _gemini_configured and _gemini_client:
        return True
    
    try:
        _gemini_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=GCP_REGION
        )
        _gemini_configured = True
        logger.info("Gemini configured successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")
        raise e

def get_gemini_client():
    """Get the singleton Gemini client instance"""
    global _gemini_client
    if _gemini_client is None:
        configure_gemini()
    return _gemini_client

def init_ai_clients():
    """Initialize AI service clients"""
    global cost_monitor
    
    # Configure Gemini
    configure_gemini()
    
    # Initialize cost monitoring
    cost_monitor = CostMonitor()
    
    print("AI clients initialized successfully")

class CostMonitor:
    def __init__(self):
        self.daily_limits = {
            'gemini_requests': 1000,    # Conservative limit
            'document_processing': 100   # Per day limit
        }
        self.usage_tracking = {}
    
    def check_limits(self, service: str) -> bool:
        today = datetime.now().date()
        key = f"{service}_{today}"
        
        current_usage = self.usage_tracking.get(key, 0)
        limit = self.daily_limits.get(service, 100)
        
        if current_usage >= limit:
            raise HTTPException(
                status_code=429, 
                detail=f"Daily limit reached for {service}. Try again tomorrow."
            )
        
        self.usage_tracking[key] = current_usage + 1
        return True

def monitor_usage(service_name: str):
    """Decorator to monitor API usage"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if cost_monitor:
                cost_monitor.check_limits(service_name)
            return await func(*args, **kwargs)
        return wrapper
    return decorator