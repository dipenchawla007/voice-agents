"""
General information agent for product and policy questions.

This module implements a general information specialist agent as part of the
multi-tenant voice agent system.
"""

import logging
from typing import Annotated, Optional, Dict, List, Any, Tuple

from livekit.agents import Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai
from pydantic import Field

from services.voice.base_agent import BaseAgent, CustomerData, RunContext_T, VOICES

# Set up logging
logger = logging.getLogger("general-agent")
logger.setLevel(logging.INFO)

class GeneralAgent(BaseAgent):
    """Agent for general inquiries and information"""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a general information specialist providing details about "
                "products, services, policies, and general inquiries. "
                "Be informative, clear, and helpful. Provide complete information "
                "while keeping responses conversational and natural for voice."
                "\n\n"
                "If a customer's question involves policy exceptions, special arrangements, "
                "or sensitive topics that need manager review, route them to the escalation agent."
            ),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(voice=VOICES["general"]),
        )
    
    @function_tool
    async def get_product_information(
        self,
        context: RunContext_T,
        product_name: Annotated[str, Field(description="Name of the product")],
    ) -> Dict[str, Any]:
        """Get information about a specific product"""
        # In a real implementation, this would query a product database
        # For this example, we're returning simulated results
        return {
            "name": product_name,
            "description": f"Our {product_name} is a premium solution for...",
            "price_range": "$99-$299",
            "features": ["Feature 1", "Feature 2", "Feature 3"]
        }
    
    @function_tool
    async def search_knowledge_base(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Search query for information")],
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base for general information"""
        # In a real implementation, this would query a vector database
        # For this example, we're returning simulated results
        return [
            {
                "title": "Company Refund Policy",
                "content": "Our refund policy allows returns within 30 days of purchase...",
                "relevance": 0.88
            },
            {
                "title": "Shipping Information",
                "content": "Standard shipping takes 3-5 business days...",
                "relevance": 0.72
            }
        ]
    
    @function_tool
    async def route_to_greeter(self, context: RunContext_T) -> tuple[Agent, str]:
        """Return to the main greeter agent"""
        return await self._transfer_to_agent("greeter", context)
    
    @function_tool
    async def route_to_escalation(self, context: RunContext_T) -> tuple[Agent, str]:
        """Transfer to the escalation agent for special policy exceptions"""
        userdata = context.userdata
        userdata.issue_type = "escalation"
        return await self._transfer_to_agent("escalation", context) 