"""
Agent model and database operations
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from sqlalchemy import select, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import Agent
from utils.logging import get_logger

logger = get_logger(__name__)

async def create_agent(
    session: AsyncSession,
    agent_id: str,
    company_id: str,
    name: str,
    description: str = None,
    voice: Dict[str, Any] = None,
    llm_config: Dict[str, Any] = None,
    asr_config: Dict[str, Any] = None,
    knowledge_base_ids: List[str] = None,
    system_prompt: str = None,
    greeting: str = None,
    avatar_url: str = None,
    status: str = "active"
) -> Agent:
    """
    Create a new agent
    """
    if voice is None:
        voice = {}
    if llm_config is None:
        llm_config = {}
    if asr_config is None:
        asr_config = {}
    if knowledge_base_ids is None:
        knowledge_base_ids = []
    
    agent = Agent(
        id=agent_id,
        company_id=company_id,
        name=name,
        description=description,
        voice=voice,
        llm_config=llm_config,
        asr_config=asr_config,
        knowledge_base_ids=knowledge_base_ids,
        system_prompt=system_prompt,
        greeting=greeting,
        avatar_url=avatar_url,
        status=status,
        created_at=datetime.utcnow()
    )
    
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    
    logger.info(f"Created agent: {agent_id}")
    return agent

async def update_agent(
    session: AsyncSession,
    agent_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    voice: Optional[Dict[str, Any]] = None,
    llm_config: Optional[Dict[str, Any]] = None,
    asr_config: Optional[Dict[str, Any]] = None,
    knowledge_base_ids: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    greeting: Optional[str] = None,
    avatar_url: Optional[str] = None,
    status: Optional[str] = None
) -> Agent:
    """
    Update an existing agent
    """
    # Get the current agent
    agent = await get_agent(session, agent_id)
    if not agent:
        raise ValueError(f"Agent not found: {agent_id}")
    
    # Prepare update data with only non-None values
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if voice is not None:
        update_data["voice"] = voice
    if llm_config is not None:
        update_data["llm_config"] = llm_config
    if asr_config is not None:
        update_data["asr_config"] = asr_config
    if knowledge_base_ids is not None:
        update_data["knowledge_base_ids"] = knowledge_base_ids
    if system_prompt is not None:
        update_data["system_prompt"] = system_prompt
    if greeting is not None:
        update_data["greeting"] = greeting
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url
    if status is not None:
        update_data["status"] = status
    
    # Update the agent
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await session.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(**update_data)
        )
        await session.commit()
    
    # Refresh and return the updated agent
    agent = await get_agent(session, agent_id)
    logger.info(f"Updated agent: {agent_id}")
    return agent

async def delete_agent(
    session: AsyncSession,
    agent_id: str
) -> bool:
    """
    Delete an agent
    """
    result = await session.execute(
        delete(Agent)
        .where(Agent.id == agent_id)
    )
    await session.commit()
    
    if result.rowcount > 0:
        logger.info(f"Deleted agent: {agent_id}")
        return True
    
    logger.warning(f"Agent not found for deletion: {agent_id}")
    return False

async def get_agent(
    session: AsyncSession,
    agent_id: str
) -> Optional[Agent]:
    """
    Get an agent by ID
    """
    result = await session.execute(
        select(Agent)
        .where(Agent.id == agent_id)
    )
    
    agent = result.scalars().first()
    return agent

async def list_agents(
    session: AsyncSession,
    company_id: str,
    limit: int = 100,
    offset: int = 0
) -> List[Agent]:
    """
    List agents for a company
    """
    result = await session.execute(
        select(Agent)
        .where(Agent.company_id == company_id)
        .order_by(Agent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    agents = result.scalars().all()
    return list(agents)

async def count_agents(
    session: AsyncSession,
    company_id: str
) -> int:
    """
    Count agents for a company
    """
    result = await session.execute(
        select(Agent)
        .where(Agent.company_id == company_id)
    )
    
    agents = result.scalars().all()
    return len(list(agents)) 