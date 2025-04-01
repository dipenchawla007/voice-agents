"""
LangGraph-enhanced greeter agent implementation.

This module provides a modified version of the greeter agent that integrates
with LangGraph for conversation flow management.
"""

import logging
from typing import Annotated, Dict, Any, Optional, Tuple

from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import openai
from pydantic import Field

from services.voice.base_agent import BaseAgent, CustomerData, RunContext_T, VOICES
from services.voice.langgraph_adapter import LangGraphAdapter

# Set up logging
logger = logging.getLogger("langgraph-greeter")
logger.setLevel(logging.INFO)

class LangGraphGreeterAgent(BaseAgent):
    """
    A greeter agent that uses LangGraph for enhanced conversation management.
    
    This agent demonstrates direct integration with LangGraph (as opposed to
    using the adapter wrapper approach) by adding special function tools that
    interact with the graph controller.
    """
    
    def __init__(self, adapter: LangGraphAdapter):
        """Initialize with the LangGraph adapter."""
        super().__init__(
            instructions=(
                "You are the first point of contact for customer support. "
                "Your job is to greet the caller warmly, understand their issue, "
                "and route them to the appropriate specialist. "
                "Ask for their name and briefly identify their issue type before routing."
                "\n\n"
                "This version uses LangGraph for enhanced conversation flow management. "
                "Use the analyze_with_langgraph tool for complex decisions."
            ),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(voice=VOICES["greeter"]),
        )
        self.adapter = adapter
        logger.info("Initialized LangGraph-enhanced greeter agent")
    
    async def on_enter(self) -> None:
        """Called when the agent becomes active."""
        # Call the standard BaseAgent on_enter first
        await super().on_enter()
        
        # Additional LangGraph-specific setup
        session_id = str(self.session.id)
        userdata: CustomerData = self.session.userdata
        
        # Register with the LangGraph adapter if not already registered
        if session_id not in self.adapter.sessions:
            await self.adapter.register_session(session_id, RunContext(self.session, userdata))
            
        logger.info(f"LangGraph greeter agent entered for session {session_id}")
    
    @function_tool
    async def update_customer_name(
        self,
        context: RunContext_T,
        name: Annotated[str, Field(description="The customer's name")]
    ) -> str:
        """Called when the customer provides their name."""
        userdata = context.userdata
        userdata.customer_name = name
        
        # Use LangGraph to generate a personalized greeting
        session_id = str(context.session.id)
        greeting_result = await self.adapter.process_user_message(
            message=f"My name is {name}",
            livekit_session_id=session_id,
            live_context=context
        )
        
        # Use the LangGraph-generated response if available, otherwise use default
        if greeting_result and "response" in greeting_result:
            response = greeting_result["response"]
            # Strip the agent tag if it exists
            if response.startswith("[GREETER]"):
                response = response[len("[GREETER]"):].strip()
            return response
        else:
            return f"Thank you, {name}. How can I help you today?"
    
    @function_tool
    async def analyze_with_langgraph(
        self,
        context: RunContext_T,
        user_query: Annotated[str, Field(description="The customer's query or statement to analyze")]
    ) -> Dict[str, Any]:
        """
        Use LangGraph to analyze the customer's request and determine next steps.
        
        This tool uses the LangGraph controller to analyze the customer's message,
        determine intent, sentiment, required verification, and suggested routing.
        """
        session_id = str(context.session.id)
        
        # Process through LangGraph
        result = await self.adapter.process_user_message(
            message=user_query,
            livekit_session_id=session_id,
            live_context=context
        )
        
        # Create a summary for the agent
        analysis_summary = {
            "intent": result.get("active_agent", "unknown"),
            "sentiment": result.get("sentiment", "neutral"),
            "verification_required": not result.get("verification_status", False),
            "suggested_routing": result.get("active_agent") 
                if result.get("active_agent") != "greeter" else None,
        }
        
        # Add this information to the context for other tools to use
        if "suggested_routing" in analysis_summary and analysis_summary["suggested_routing"]:
            context.userdata.issue_type = analysis_summary["suggested_routing"]
        
        return analysis_summary
    
    @function_tool
    async def route_to_billing(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a billing-related issue."""
        userdata = context.userdata
        userdata.issue_type = "billing"
        
        # Confirm with LangGraph if this is the right routing
        session_id = str(context.session.id)
        routing_result = await self.adapter.process_user_message(
            message="I need help with billing",
            livekit_session_id=session_id,
            live_context=context
        )
        
        # LangGraph might suggest a different routing based on context
        suggested_routing = routing_result.get("active_agent")
        if suggested_routing and suggested_routing != "billing":
            # Override with LangGraph's suggestion
            userdata.issue_type = suggested_routing
            return await self._transfer_to_agent(suggested_routing, context)
            
        # Proceed with billing routing
        return await self._transfer_to_agent("billing", context)
    
    @function_tool
    async def route_to_technical(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a technical issue."""
        userdata = context.userdata
        userdata.issue_type = "technical"
        
        # Confirm with LangGraph if this is the right routing
        session_id = str(context.session.id)
        routing_result = await self.adapter.process_user_message(
            message="I need technical support",
            livekit_session_id=session_id,
            live_context=context
        )
        
        # LangGraph might suggest a different routing based on context
        suggested_routing = routing_result.get("active_agent")
        if suggested_routing and suggested_routing != "technical":
            # Override with LangGraph's suggestion
            userdata.issue_type = suggested_routing
            return await self._transfer_to_agent(suggested_routing, context)
            
        # Proceed with technical routing
        return await self._transfer_to_agent("technical", context)
    
    @function_tool
    async def route_to_general(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a general inquiry or information request."""
        userdata = context.userdata
        userdata.issue_type = "general"
        
        # Let LangGraph know about this routing decision
        session_id = str(context.session.id)
        await self.adapter.process_user_message(
            message="I need general information",
            livekit_session_id=session_id,
            live_context=context
        )
        
        return await self._transfer_to_agent("general", context)
    
    @function_tool
    async def route_to_escalation(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a complex issue requiring manager intervention."""
        userdata = context.userdata
        userdata.issue_type = "escalation"
        
        # Let LangGraph know about this routing decision
        session_id = str(context.session.id)
        await self.adapter.process_user_message(
            message="I need to speak to a manager",
            livekit_session_id=session_id,
            live_context=context
        )
        
        return await self._transfer_to_agent("escalation", context)
    
    @function_tool
    async def route_with_langgraph(self, context: RunContext_T) -> tuple[Agent, str]:
        """
        Let LangGraph determine the best routing based on the conversation context.
        
        This tool defers the routing decision entirely to the LangGraph controller,
        which analyzes the full conversation history to determine the most appropriate
        specialist agent.
        """
        session_id = str(context.session.id)
        
        # Get LangGraph's routing recommendation
        routing_result = await self.adapter.process_user_message(
            message="Where should I be routed?",
            livekit_session_id=session_id,
            live_context=context
        )
        
        # Extract the suggested routing
        suggested_routing = routing_result.get("active_agent")
        
        if suggested_routing and suggested_routing != "greeter":
            # Update user data with the routing
            context.userdata.issue_type = suggested_routing
            
            # Return the transfer command
            return await self._transfer_to_agent(suggested_routing, context)
        else:
            # If no clear routing or staying with greeter, create a response
            message = "I'll continue helping you. What specific information do you need?"
            return context.session.current_agent, message 