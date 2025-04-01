"""
Technical support agent for handling product and service issues.

This module implements a technical support specialist agent as part of the
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
logger = logging.getLogger("technical-agent")
logger.setLevel(logging.INFO)

class TechnicalAgent(BaseAgent):
    """Specialist agent for technical issues"""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a technical support specialist helping customers with "
                "product functionality, troubleshooting, and technical problems. "
                "Guide customers through diagnosis and resolution steps clearly. "
                "For complex issues, create support tickets when necessary."
                "\n\n"
                "If the issue requires special handling or if the customer is particularly "
                "frustrated after trying multiple solutions, route them to the escalation agent."
            ),
            llm=openai.LLM(model="gpt-4o"),
            tts=openai.TTS(voice=VOICES["technical"]),
        )
    
    @function_tool
    async def search_knowledge_base(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Search query for technical solutions")],
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base for technical solutions"""
        # In a real implementation, this would query a vector database
        # For this example, we're returning simulated results
        return [
            {
                "title": "Troubleshooting Network Connection Issues",
                "content": "1. Check your internet connection. 2. Restart your router...",
                "relevance": 0.92
            },
            {
                "title": "Reset Your Password",
                "content": "To reset your password, visit the login page and click 'Forgot Password'...",
                "relevance": 0.76
            }
        ]
    
    @function_tool
    async def create_support_ticket(
        self,
        context: RunContext_T,
        issue_summary: Annotated[str, Field(description="Brief summary of the issue")],
        severity: Annotated[str, Field(description="Issue severity (low, medium, high, critical)")] = "medium",
    ) -> Dict[str, Any]:
        """Create a support ticket for issues requiring further assistance"""
        userdata = context.userdata
        
        # In a real implementation, this would create a ticket in a system like Zendesk
        ticket_id = f"ticket_{hash(issue_summary) % 10000}"
        userdata.ticket_id = ticket_id
        
        return {
            "ticket_id": ticket_id,
            "status": "created",
            "estimated_response_time": "24 hours" if severity != "critical" else "4 hours"
        }
    
    @function_tool
    async def route_to_greeter(self, context: RunContext_T) -> tuple[Agent, str]:
        """Return to the main greeter agent"""
        return await self._transfer_to_agent("greeter", context)
    
    @function_tool
    async def route_to_escalation(self, context: RunContext_T) -> tuple[Agent, str]:
        """Transfer to the escalation agent for special handling"""
        userdata = context.userdata
        userdata.issue_type = "escalation"
        return await self._transfer_to_agent("escalation", context) 