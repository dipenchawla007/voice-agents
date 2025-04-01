"""
Main API router for the voice agent multi-tenant system
"""
from fastapi import APIRouter

from api.routes import companies, agents, tokens, knowledge_bases

# Create main API router
api_router = APIRouter()

# Register route modules
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["knowledge_bases"]) 