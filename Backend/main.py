# FastAPI application

# main.py - FastAPI Application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import sys
import os
from utils.ai_client import cost_monitor

# Add the Backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routers import analysis, documents, agent, user_routes
from models.database import init_firebase
from utils.ai_client import init_ai_clients

app = FastAPI(title="AI Startup Analyst", version="1.0.0")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://ventureval-ef705.web.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
@app.on_event("startup")
async def startup_event():
    print("Starting up...")
    init_firebase()
    init_ai_clients()

# Include routers
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(user_routes.router)

@app.get("/")
async def root():
    return {"message": "AI Startup Analyst API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/api/admin/usage")
async def get_usage_stats():
    """Get current usage statistics"""
    
    if cost_monitor:
        return {
            'daily_usage': cost_monitor.usage_tracking,
            'limits': cost_monitor.daily_limits,
            'status': 'active'
        }
    
    return {'status': 'monitoring_unavailable'}

