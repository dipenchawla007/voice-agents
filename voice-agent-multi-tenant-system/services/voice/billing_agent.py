"""
Billing agent for handling payment and account issues.

This module implements a billing specialist agent as part of the
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
logger = logging.getLogger("billing-agent")
logger.setLevel(logging.INFO)

class BillingAgent(BaseAgent):
    """Specialist agent for billing issues"""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a billing specialist helping customers with payment issues, "
                "refunds, subscription concerns, and invoice questions. "
                "Always verify the customer's identity before providing account-specific details. "
                "Be empathetic but follow security protocols strictly."
                "\n\n"
                "For special refund requests outside of policy, disputed charges, or issues "
                "requiring manager approval, route the customer to the escalation agent."
            ),
            llm=openai.LLM(model="gpt-4o"),
            tts=openai.TTS(voice=VOICES["billing"]),
        )
    
    @function_tool
    async def verify_customer_identity(
        self,
        context: RunContext_T,
        email: Annotated[str, Field(description="Customer's email address")],
        order_id: Optional[Annotated[str, Field(description="Order ID if relevant")]] = None,
    ) -> Dict[str, Any]:
        """Verify customer identity using their email and optionally an order ID"""
        userdata = context.userdata
        
        # In a real implementation, this would check against a database
        # For this example, we're simulating a successful verification
        userdata.customer_email = email
        userdata.verification_status = True
        
        if order_id:
            userdata.order_id = order_id
            
            # Simulate fetching order details
            userdata.order_details = {
                "order_id": order_id,
                "purchase_date": "2023-05-15",
                "amount": 89.99,
                "status": "processed"
            }
        
        return {
            "verified": True,
            "customer_id": "cust_12345",  # Simulated ID
        }
    
    @function_tool
    async def process_refund(
        self,
        context: RunContext_T,
        order_id: Annotated[str, Field(description="Order ID to refund")],
        reason: Annotated[str, Field(description="Reason for refund")],
    ) -> Dict[str, Any]:
        """Process a refund for a customer order"""
        userdata = context.userdata
        
        # Security check
        if not userdata.verification_status:
            return {"status": "failed", "reason": "Customer identity not verified"}
        
        # In a real implementation, this would call a payment processing API
        # For this example, we're simulating a successful refund
        return {
            "status": "success",
            "refund_id": f"ref_{hash(order_id) % 10000}",
            "amount": userdata.order_details.get("amount") if userdata.order_details else 0,
            "estimated_processing_days": 3
        }
    
    @function_tool
    async def route_to_greeter(self, context: RunContext_T) -> tuple[Agent, str]:
        """Return to the main greeter agent"""
        return await self._transfer_to_agent("greeter", context)
    
    @function_tool
    async def route_to_escalation(self, context: RunContext_T) -> tuple[Agent, str]:
        """Transfer to the escalation agent for special billing exceptions"""
        userdata = context.userdata
        userdata.issue_type = "escalation"
        return await self._transfer_to_agent("escalation", context) 