"""
Greeter agent that serves as the first contact point for customers.

This module implements a greeter agent that routes customers to specialized agents
based on their needs.
"""

import logging
from typing import Annotated, Optional, Dict, List, Any, Tuple

from livekit.agents import Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai
from pydantic import Field

from services.voice.base_agent import BaseAgent, CustomerData, RunContext_T, VOICES

# Set up logging
logger = logging.getLogger("greeter-agent")
logger.setLevel(logging.INFO)

class GreeterAgent(BaseAgent):
    """Initial agent that greets customers and routes to specialists"""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are the first point of contact for customer support. "
                "Your job is to greet the caller warmly, understand their issue, "
                "and route them to the appropriate specialist. "
                "Ask for their name and briefly identify their issue type before routing."
                "\n\n"
                "For complex issues that seem to require special handling, manager intervention, "
                "or exceptions to normal policies, route to the escalation agent."
            ),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(voice=VOICES["greeter"]),
        )
    
    @function_tool
    async def update_customer_name(
        self,
        context: RunContext_T,
        name: Annotated[str, Field(description="The customer's name")]
    ) -> str:
        """Called when the customer provides their name"""
        userdata = context.userdata
        userdata.customer_name = name
        return f"Thank you, {name}. How can I help you today?"
    
    @function_tool
    async def route_to_billing(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a billing-related issue"""
        userdata = context.userdata
        userdata.issue_type = "billing"
        return await self._transfer_to_agent("billing", context)
    
    @function_tool
    async def route_to_technical(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a technical issue"""
        userdata = context.userdata
        userdata.issue_type = "technical"
        return await self._transfer_to_agent("technical", context)
    
    @function_tool
    async def route_to_general(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a general inquiry or information request"""
        userdata = context.userdata
        userdata.issue_type = "general"
        return await self._transfer_to_agent("general", context)
    
    @function_tool
    async def route_to_escalation(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the customer has a complex issue requiring manager intervention"""
        userdata = context.userdata
        userdata.issue_type = "escalation"
        return await self._transfer_to_agent("escalation", context) 