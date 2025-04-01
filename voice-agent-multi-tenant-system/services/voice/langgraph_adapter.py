"""
LangGraph adapter for LiveKit voice agents.

This module provides the adapter that connects the LangGraph controller
with the LiveKit voice agents, serving as the integration layer between
the two systems.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple

from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool

from services.voice.base_agent import CustomerData, RunContext_T
from services.voice.graph_controller import GraphController

# Set up logging
logger = logging.getLogger("langgraph-adapter")
logger.setLevel(logging.INFO)

class LangGraphAdapter:
    """
    Adapter class that bridges between LiveKit agents and the LangGraph controller.
    
    This adapter handles the integration between the graph-based conversation flow management
    provided by LangGraph and the voice agent capabilities provided by LiveKit Agents SDK.
    """
    
    def __init__(self, company_id: str):
        """Initialize the adapter with company context."""
        self.company_id = company_id
        self.graph_controller = GraphController(company_id)
        self.sessions: Dict[str, str] = {}  # Maps LiveKit session IDs to graph session IDs
        logger.info(f"Initialized LangGraph adapter for company {company_id}")
    
    async def register_session(self, livekit_session_id: str, live_context: RunContext_T) -> str:
        """Register a new session with the adapter."""
        # Create a new session with the graph controller
        graph_session_id = await self.graph_controller.create_session(live_context)
        
        # Store the mapping
        self.sessions[livekit_session_id] = graph_session_id
        
        logger.info(f"Registered new session: LiveKit({livekit_session_id}) -> Graph({graph_session_id})")
        return graph_session_id
    
    async def process_user_message(
        self, 
        message: str,
        livekit_session_id: str,
        live_context: RunContext_T
    ) -> Dict[str, Any]:
        """
        Process a user message using the LangGraph controller.
        
        This method serves as the main integration point between LiveKit and LangGraph,
        routing user messages through the graph controller and returning the results.
        
        Args:
            message: User's text message
            livekit_session_id: The LiveKit session identifier
            live_context: The LiveKit RunContext with CustomerData
            
        Returns:
            A dict with the response and other state information
        """
        # Get the graph session ID
        graph_session_id = self.sessions.get(livekit_session_id)
        
        if not graph_session_id:
            # Create a new session if one doesn't exist
            graph_session_id = await self.register_session(livekit_session_id, live_context)
        
        # Process the message through the graph controller
        result = await self.graph_controller.process_message(
            user_message=message,
            session_id=graph_session_id,
            live_context=live_context
        )
        
        logger.info(f"Processed message for session {livekit_session_id}, active agent: {result['active_agent']}")
        return result
    
    async def get_suggested_routing(
        self,
        livekit_session_id: str,
        live_context: RunContext_T
    ) -> Optional[str]:
        """
        Get the suggested agent routing based on the current graph state.
        
        Args:
            livekit_session_id: The LiveKit session identifier
            live_context: The LiveKit RunContext with CustomerData
            
        Returns:
            The suggested agent name or None if no routing is suggested
        """
        # This is just a placeholder in this implementation
        # In a real implementation, we would query the graph controller for the current active agent
        graph_session_id = self.sessions.get(livekit_session_id)
        
        if not graph_session_id:
            return None
            
        # For now, we'll just return whatever is in the customer data's issue_type
        # In a full implementation, this would be more sophisticated
        return live_context.userdata.issue_type


class LangGraphEnabledAgent(Agent):
    """
    A LiveKit agent that uses LangGraph for conversation flow management.
    
    This agent class wraps the normal LiveKit agent functionality but delegates
    conversation flow decisions to the LangGraph controller.
    """
    
    def __init__(
        self, 
        base_agent: Agent,
        adapter: LangGraphAdapter,
        company_id: str
    ):
        """
        Initialize the LangGraph-enabled agent.
        
        Args:
            base_agent: The underlying LiveKit agent to wrap
            adapter: The LangGraph adapter
            company_id: The company ID for multi-tenant isolation
        """
        super().__init__(
            instructions=base_agent.instructions,
            llm=base_agent.llm,
            tts=base_agent.tts
        )
        self.base_agent = base_agent
        self.adapter = adapter
        self.company_id = company_id
        logger.info(f"Created LangGraph-enabled agent wrapper for {type(base_agent).__name__}")
    
    async def on_enter(self) -> None:
        """Called when the agent becomes active."""
        # First call the base agent's on_enter
        await self.base_agent.on_enter()
        
        # Then add our own LangGraph-specific processing
        session_id = str(self.session.id)
        userdata: CustomerData = self.session.userdata
        
        # Register with the LangGraph adapter if not already registered
        if session_id not in self.adapter.sessions:
            await self.adapter.register_session(session_id, RunContext(self.session, userdata))
            
        logger.info(f"LangGraph-enabled agent {type(self.base_agent).__name__} entered for session {session_id}")
    
    @function_tool
    async def delegate_to_langgraph(
        self,
        context: RunContext_T,
        message: str
    ) -> Dict[str, Any]:
        """
        Delegate message processing to the LangGraph controller.
        
        This function tool is the bridge between LiveKit agent function calling
        and the LangGraph controller's conversation management.
        
        Args:
            context: The LiveKit run context
            message: The user's message to process
            
        Returns:
            The processed result from the LangGraph controller
        """
        session_id = str(context.session.id)
        
        # Process the message through the LangGraph adapter
        result = await self.adapter.process_user_message(
            message=message,
            livekit_session_id=session_id,
            live_context=context
        )
        
        # Check if we need to route to a different agent
        suggested_agent = result.get("active_agent")
        current_agent = context.session.current_agent.__class__.__name__.lower().replace("agent", "")
        
        if suggested_agent and suggested_agent != current_agent:
            # Store this in the context for later routing
            context.userdata.issue_type = suggested_agent
        
        return {
            "response": result["response"],
            "sentiment": result["sentiment"],
            "verification_status": result["verification_status"],
            "routing_suggestion": suggested_agent if suggested_agent != current_agent else None
        }
        
    async def _get_graph_suggested_routing(self, context: RunContext_T) -> Optional[str]:
        """Get routing suggestions from the LangGraph controller."""
        session_id = str(context.session.id)
        return await self.adapter.get_suggested_routing(session_id, context)


def create_langgraph_enabled_agent(
    base_agent: Agent,
    adapter: LangGraphAdapter,
    company_id: str
) -> Agent:
    """
    Factory function to create a LangGraph-enabled agent.
    
    Args:
        base_agent: The underlying LiveKit agent
        adapter: The LangGraph adapter
        company_id: The company ID for multi-tenant isolation
        
    Returns:
        A LangGraph-enabled agent that wraps the base agent
    """
    return LangGraphEnabledAgent(base_agent, adapter, company_id) 