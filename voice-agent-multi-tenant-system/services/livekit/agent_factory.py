"""
LiveKit Agent Factory Service.

This service handles the creation of LiveKit agents with knowledge base integration.
"""

import logging
import os
from typing import Dict, List, Optional, Any

from services.knowledge_base.manager import KnowledgeBaseManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.schemas import Agent, KnowledgeBase

logger = logging.getLogger(__name__)

class LiveKitAgentFactory:
    """Factory for creating LiveKit agents with knowledge base support"""
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the LiveKit agent factory
        
        Args:
            db_session: SQLAlchemy async session for database operations
        """
        self.db_session = db_session
        self.kb_manager = KnowledgeBaseManager(db_session)
        
        # API keys for various services
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    
    async def create_agent_config(self, 
                                 agent_id: str, 
                                 company_id: str) -> Dict[str, Any]:
        """
        Create a configuration for a LiveKit agent with knowledge base integration
        
        Args:
            agent_id: ID of the agent
            company_id: ID of the company
            
        Returns:
            A configuration dictionary for LiveKit agent creation
        """
        # Get agent from database
        agent_query = select(Agent).where(
            Agent.id == agent_id,
            Agent.company_id == company_id
        )
        result = await self.db_session.execute(agent_query)
        agent = result.scalars().first()
        
        if not agent:
            raise ValueError(f"Agent {agent_id} not found for company {company_id}")
        
        # Create base configuration
        agent_config = {
            "agent_id": agent.id,
            "company_id": agent.company_id,
            "name": agent.name,
            "greeting": agent.greeting,
            "system_prompt": agent.system_prompt,
            "llm_config": agent.llm_config,
            "voice_config": agent.voice,
            "asr_config": agent.asr_config,
        }
        
        # Process knowledge base integration if agent has knowledge bases
        if agent.knowledge_base_ids:
            knowledge_bases = []
            
            for kb_id in agent.knowledge_base_ids:
                kb = await self.kb_manager.get_knowledge_base(company_id, kb_id)
                if kb:
                    knowledge_bases.append(kb)
            
            # Add knowledge base configuration if knowledge bases were found
            if knowledge_bases:
                agent_config["knowledge_base"] = {
                    "enabled": True,
                    "kb_ids": agent.knowledge_base_ids,
                    "kb_info": knowledge_bases
                }
                
                # Enhance the system prompt with knowledge base information
                kb_context = "This agent has access to the following knowledge bases:\n"
                for kb in knowledge_bases:
                    kb_context += f"- {kb['name']}: {kb['description'] or 'No description'}\n"
                
                agent_config["system_prompt"] = f"{agent_config['system_prompt']}\n\n{kb_context}"
        
        return agent_config
    
    async def generate_livekit_agent_config(self, 
                                           agent_id: str, 
                                           company_id: str,
                                           user_id: Optional[str] = None,
                                           session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a complete LiveKit agent configuration that can be used to create a real agent
        
        Args:
            agent_id: ID of the agent
            company_id: ID of the company
            user_id: Optional ID of the user
            session_id: Optional session ID
            
        Returns:
            A complete LiveKit agent configuration
        """
        # Get basic agent configuration
        agent_config = await self.create_agent_config(agent_id, company_id)
        
        # Configure LLM based on agent settings
        llm_type = agent_config["llm_config"].get("type", "openai")
        llm_model = agent_config["llm_config"].get("model", "gpt-4o-mini")
        
        # Configure TTS based on agent settings
        tts_type = agent_config["voice_config"].get("type", "elevenlabs")
        voice_id = agent_config["voice_config"].get("voice_id")
        
        # Configure ASR
        asr_type = agent_config["asr_config"].get("type", "deepgram")
        
        # Basic LiveKit agent configuration
        livekit_config = {
            "vad": {
                "type": "silero"
            },
            "stt": {
                "type": asr_type,
                "model": agent_config["asr_config"].get("model", "nova-2"),
                "api_key": self.deepgram_api_key
            },
            "llm": {
                "type": llm_type,
                "model": llm_model,
                "api_key": self._get_llm_api_key(llm_type),
                "system_message": agent_config["system_prompt"],
                "temperature": agent_config["llm_config"].get("temperature", 0.7)
            },
            "tts": {
                "type": tts_type,
                "voice": voice_id,
                "api_key": self.elevenlabs_api_key
            },
            "metadata": {
                "agent_id": agent_id,
                "company_id": company_id,
                "user_id": user_id,
                "session_id": session_id
            }
        }
        
        # Add knowledge base retrieval if available
        if "knowledge_base" in agent_config and agent_config["knowledge_base"]["enabled"]:
            # In a real implementation, this would configure RAG properly
            # For now, just add a placeholder
            livekit_config["llm"]["rag_enabled"] = True
            livekit_config["llm"]["knowledge_base_ids"] = agent_config["knowledge_base"]["kb_ids"]
            
            # This would be used to create a real RAG system using LlamaIndex or similar
            # with the Pinecone vector store and proper embedding model
            
        return livekit_config
    
    def _get_llm_api_key(self, llm_type: str) -> Optional[str]:
        """Get the appropriate API key for the LLM type"""
        if llm_type == "openai":
            return self.openai_api_key
        elif llm_type == "anthropic":
            return self.anthropic_api_key
        else:
            return None 