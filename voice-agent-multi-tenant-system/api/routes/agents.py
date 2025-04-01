"""
API routes for agent management
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Path, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import async_session
from models.company import get_company_by_api_key
from models.agent import create_agent, update_agent, get_agent, list_agents, delete_agent
from services.quota.manager import QuotaManager
from services.usage_tracking.tracker import UsageTracker
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

async def get_db():
    """Dependency for database session"""
    async with async_session() as session:
        yield session

async def validate_company_api_key(
    session: AsyncSession,
    x_api_key: Optional[str] = Header(None)
):
    """Validate company API key and return company"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    
    company = await get_company_by_api_key(session, x_api_key)
    if not company:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return company

@router.post("/", response_model=Dict[str, Any])
async def create_new_agent(
    request: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Create a new agent for a company
    
    Required request body:
    - company_id: Company ID
    - name: Agent name
    - description: Agent description
    - voice: Voice configuration
    - llm_config: LLM configuration
    - asr_config: ASR configuration
    - knowledge_base_ids: List of knowledge base IDs (optional)
    - system_prompt: System prompt for the agent
    - greeting: Agent greeting message
    
    Returns:
        Agent data
    """
    # Validate company API key
    company = await validate_company_api_key(session, x_api_key)
    
    # Get parameters
    company_id = request.get("company_id")
    
    # Validate company ID matches API key's company
    if company_id != company.id:
        raise HTTPException(status_code=403, detail="API key does not match company ID")
    
    # Get required parameters
    name = request.get("name")
    description = request.get("description")
    voice = request.get("voice", {})
    llm_config = request.get("llm_config", {})
    asr_config = request.get("asr_config", {})
    knowledge_base_ids = request.get("knowledge_base_ids", [])
    system_prompt = request.get("system_prompt", "")
    greeting = request.get("greeting", "")
    
    # Validate required parameters
    if not name:
        raise HTTPException(status_code=400, detail="Agent name is required")
    
    # Check quota before creating agent
    quota_manager = QuotaManager()
    quota_check = await quota_manager.check_agent_quota(session, company_id)
    
    if not quota_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"Agent quota exceeded: {quota_check['current']}/{quota_check['limit']} agents"
        )
    
    # Create agent
    try:
        # Generate a unique agent ID
        agent_id = str(uuid4())
        
        # Create agent in DB
        agent = await create_agent(
            session,
            agent_id=agent_id,
            company_id=company_id,
            name=name,
            description=description,
            voice=voice,
            llm_config=llm_config,
            asr_config=asr_config,
            knowledge_base_ids=knowledge_base_ids,
            system_prompt=system_prompt,
            greeting=greeting
        )
        
        logger.info(f"Created new agent: {agent_id}, {name} for company {company_id}")
        
        # Return agent data
        return {
            "id": agent.id,
            "company_id": agent.company_id,
            "name": agent.name,
            "description": agent.description,
            "voice": agent.voice,
            "llm_config": agent.llm_config,
            "asr_config": agent.asr_config,
            "knowledge_base_ids": agent.knowledge_base_ids,
            "system_prompt": agent.system_prompt,
            "greeting": agent.greeting,
            "created_at": agent.created_at,
            "status": agent.status
        }
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating agent: {str(e)}")

@router.get("/", response_model=List[Dict[str, Any]])
async def get_agents(
    company_id: str = Query(..., description="Company ID"),
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List agents for a company
    
    Returns:
        List of agents
    """
    # Validate company API key
    company = await validate_company_api_key(session, x_api_key)
    
    # Validate company ID matches API key's company
    if company_id != company.id:
        raise HTTPException(status_code=403, detail="API key does not match company ID")
    
    # Get agents
    try:
        agents = await list_agents(session, company_id, limit=limit, offset=offset)
        
        # Format response
        result = []
        for agent in agents:
            result.append({
                "id": agent.id,
                "company_id": agent.company_id,
                "name": agent.name,
                "description": agent.description,
                "created_at": agent.created_at,
                "status": agent.status
            })
        
        return result
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing agents: {str(e)}")

@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_agent_details(
    agent_id: str = Path(..., description="Agent ID"),
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get agent details
    
    Returns:
        Agent data
    """
    # Validate company API key
    company = await validate_company_api_key(session, x_api_key)
    
    # Get agent
    try:
        agent = await get_agent(session, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Validate company has access to this agent
        if agent.company_id != company.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Return agent data
        return {
            "id": agent.id,
            "company_id": agent.company_id,
            "name": agent.name,
            "description": agent.description,
            "voice": agent.voice,
            "llm_config": agent.llm_config,
            "asr_config": agent.asr_config,
            "knowledge_base_ids": agent.knowledge_base_ids,
            "system_prompt": agent.system_prompt,
            "greeting": agent.greeting,
            "created_at": agent.created_at,
            "status": agent.status
        }
    except Exception as e:
        logger.error(f"Error getting agent details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting agent details: {str(e)}")

@router.put("/{agent_id}", response_model=Dict[str, Any])
async def update_agent_details(
    request: Dict[str, Any],
    agent_id: str = Path(..., description="Agent ID"),
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Update agent details
    
    Request body can include:
    - name: Agent name
    - description: Agent description
    - voice: Voice configuration
    - llm_config: LLM configuration
    - asr_config: ASR configuration
    - knowledge_base_ids: List of knowledge base IDs
    - system_prompt: System prompt for the agent
    - greeting: Agent greeting message
    - status: Agent status (active, disabled)
    
    Returns:
        Updated agent data
    """
    # Validate company API key
    company = await validate_company_api_key(session, x_api_key)
    
    # Get agent
    agent = await get_agent(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Validate company has access to this agent
    if agent.company_id != company.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update agent
    try:
        updated_agent = await update_agent(
            session,
            agent_id=agent_id,
            name=request.get("name"),
            description=request.get("description"),
            voice=request.get("voice"),
            llm_config=request.get("llm_config"),
            asr_config=request.get("asr_config"),
            knowledge_base_ids=request.get("knowledge_base_ids"),
            system_prompt=request.get("system_prompt"),
            greeting=request.get("greeting"),
            status=request.get("status")
        )
        
        logger.info(f"Updated agent: {agent_id}")
        
        # Return updated agent data
        return {
            "id": updated_agent.id,
            "company_id": updated_agent.company_id,
            "name": updated_agent.name,
            "description": updated_agent.description,
            "voice": updated_agent.voice,
            "llm_config": updated_agent.llm_config,
            "asr_config": updated_agent.asr_config,
            "knowledge_base_ids": updated_agent.knowledge_base_ids,
            "system_prompt": updated_agent.system_prompt,
            "greeting": updated_agent.greeting,
            "created_at": updated_agent.created_at,
            "status": updated_agent.status
        }
    except Exception as e:
        logger.error(f"Error updating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating agent: {str(e)}")

@router.delete("/{agent_id}")
async def remove_agent(
    agent_id: str = Path(..., description="Agent ID"),
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Delete an agent
    
    Returns:
        Success message
    """
    # Validate company API key
    company = await validate_company_api_key(session, x_api_key)
    
    # Get agent
    agent = await get_agent(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Validate company has access to this agent
    if agent.company_id != company.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete agent
    try:
        await delete_agent(session, agent_id)
        
        logger.info(f"Deleted agent: {agent_id}")
        
        # Return success
        return {
            "success": True,
            "message": f"Agent {agent_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting agent: {str(e)}")

@router.post("/{agent_id}/avatar", response_model=Dict[str, Any])
async def upload_agent_avatar(
    agent_id: str = Path(..., description="Agent ID"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Upload an avatar image for an agent
    
    Returns:
        Success message and avatar URL
    """
    # Validate company API key
    company = await validate_company_api_key(session, x_api_key)
    
    # Get agent
    agent = await get_agent(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Validate company has access to this agent
    if agent.company_id != company.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate file type
    allowed_extensions = [".jpg", ".jpeg", ".png"]
    file_ext = file.filename.lower().split(".")[-1]
    
    if f".{file_ext}" not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # TODO: Implement file storage logic
    # For now, we'll just pretend we saved it
    avatar_url = f"/avatars/{agent_id}.{file_ext}"
    
    # Update agent with avatar URL
    try:
        updated_agent = await update_agent(
            session,
            agent_id=agent_id,
            avatar_url=avatar_url
        )
        
        logger.info(f"Uploaded avatar for agent: {agent_id}")
        
        # Return success
        return {
            "success": True,
            "avatar_url": avatar_url
        }
    except Exception as e:
        logger.error(f"Error uploading avatar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading avatar: {str(e)}")

@router.get("/{agent_id}/usage", response_model=Dict[str, Any])
async def get_agent_usage(
    agent_id: str = Path(..., description="Agent ID"),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get usage statistics for an agent
    
    Returns:
        Usage data
    """
    # Validate company API key
    company = await validate_company_api_key(session, x_api_key)
    
    # Get agent
    agent = await get_agent(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Validate company has access to this agent
    if agent.company_id != company.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get usage data
    try:
        usage_tracker = UsageTracker()
        usage_data = await usage_tracker.get_agent_usage(
            session,
            agent_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return usage_data
    except Exception as e:
        logger.error(f"Error getting agent usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting agent usage: {str(e)}") 