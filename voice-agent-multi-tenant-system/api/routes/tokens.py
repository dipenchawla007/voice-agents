"""
API routes for token generation and management
"""
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import async_session
from models.company import get_company_by_api_key
from services.livekit.token_service import token_service
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

async def get_db():
    """Dependency for database session"""
    async with async_session() as session:
        yield session

@router.post("/generate")
async def generate_token(
    request: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Generate a LiveKit token for a company's agent
    
    Required request body:
    - company_id: ID of the company
    - agent_id: ID of the agent
    - user_id: Optional user ID
    
    Returns:
        Token and room information
    """
    # Validate API key
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    
    company = await get_company_by_api_key(session, x_api_key)
    if not company:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Get parameters
    company_id = request.get("company_id")
    agent_id = request.get("agent_id")
    user_id = request.get("user_id")
    
    # Validate company_id matches the API key's company
    if company_id != company.id:
        raise HTTPException(status_code=403, detail="API key does not match company ID")
    
    # Validate required parameters
    if not company_id or not agent_id:
        raise HTTPException(status_code=400, detail="company_id and agent_id are required")
    
    # Generate token
    try:
        token, room_name = token_service.generate_room_token(
            company_id=company_id,
            agent_id=agent_id,
            user_id=user_id
        )
        
        logger.info(f"Generated token for company {company_id}, agent {agent_id}")
        
        return {
            "token": token,
            "room": room_name,
            "url": "wss://your-livekit-server.livekit.cloud",  # This should come from config
            "expires_in": 3600  # 1 hour in seconds
        }
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating token: {str(e)}")

@router.post("/agent")
async def generate_agent_token(
    request: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Generate a LiveKit token for an agent (server-side)
    
    Required request body:
    - company_id: ID of the company
    - agent_id: ID of the agent
    
    Returns:
        Token and room information for the agent
    """
    # Validate API key
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    
    company = await get_company_by_api_key(session, x_api_key)
    if not company:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Get parameters
    company_id = request.get("company_id")
    agent_id = request.get("agent_id")
    
    # Validate company_id matches the API key's company
    if company_id != company.id:
        raise HTTPException(status_code=403, detail="API key does not match company ID")
    
    # Validate required parameters
    if not company_id or not agent_id:
        raise HTTPException(status_code=400, detail="company_id and agent_id are required")
    
    # Generate token with longer expiration for agent
    try:
        token, room_name = token_service.generate_agent_token(
            company_id=company_id,
            agent_id=agent_id
        )
        
        logger.info(f"Generated agent token for company {company_id}, agent {agent_id}")
        
        return {
            "token": token,
            "room": room_name,
            "url": "wss://your-livekit-server.livekit.cloud",  # This should come from config
            "expires_in": 86400  # 24 hours in seconds
        }
    except Exception as e:
        logger.error(f"Error generating agent token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating agent token: {str(e)}")

@router.post("/validate")
async def validate_token(
    request: Dict[str, Any]
):
    """
    Validate a LiveKit token
    
    Required request body:
    - token: The token to validate
    
    Returns:
        Token claims if valid
    """
    token = request.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    try:
        decoded = token_service.validate_token(token)
        return {
            "valid": True,
            "claims": decoded
        }
    except ValueError as e:
        return {
            "valid": False,
            "reason": str(e)
        }
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating token: {str(e)}") 