"""
Escalation agent for handling complex customer issues that require manager intervention.

This module implements an escalation specialist agent as part of the multi-tenant
voice agent system using LiveKit Agents SDK.
"""

import logging
from datetime import datetime
from typing import Annotated, Optional, Dict, List, Any, Tuple

from livekit.agents import Agent, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import openai
from pydantic import Field

from services.voice.base_agent import BaseAgent, CustomerData, RunContext_T, VOICES

# Set up logging
logger = logging.getLogger("escalation-agent")
logger.setLevel(logging.INFO)

class EscalationAgent(BaseAgent):
    """
    Specialist agent for complex issues requiring manager intervention
    or special handling beyond standard customer support procedures.
    """
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are an escalation specialist handling complex customer issues that "
                "couldn't be resolved by other support agents. Your role is to provide "
                "advanced problem-solving, special exception handling, and manager-level "
                "interventions. You're authorized to make special accommodations when necessary. "
                "Be empathetic, authoritative, and solutions-oriented. For security purposes, "
                "always ensure the customer's identity has been verified before proceeding "
                "with any sensitive actions."
            ),
            llm=openai.LLM(model="gpt-4o"),  # Using full model for complex reasoning
            tts=openai.TTS(voice=VOICES.get("escalation", "alloy")),  # Using alloy as default
        )
    
    @function_tool
    async def apply_account_exception(
        self,
        context: RunContext_T,
        exception_type: Annotated[str, Field(description="Type of exception (payment, usage_limit, access)")],
        reason: Annotated[str, Field(description="Detailed reason for the exception")],
        duration_days: Annotated[int, Field(description="Number of days the exception should apply")] = 30,
    ) -> Dict[str, Any]:
        """Apply a special exception to a customer account for unique circumstances"""
        userdata = context.userdata
        
        # Security check
        if not userdata.verification_status:
            return {
                "status": "failed", 
                "reason": "Customer identity must be verified before applying exceptions"
            }
        
        # In a real implementation, this would call an API to apply the exception
        # For this example, we're simulating the process
        exception_id = f"exc_{hash(f'{userdata.customer_id}_{exception_type}') % 10000}"
        
        # Log the exception for audit purposes
        logger.info(
            f"Applied {exception_type} exception for customer {userdata.customer_id}, "
            f"duration: {duration_days} days, reason: {reason}"
        )
        
        # Store the exception details in customer data for reference
        if "exceptions" not in userdata.issue_details:
            userdata.issue_details["exceptions"] = []
            
        userdata.issue_details["exceptions"].append({
            "id": exception_id,
            "type": exception_type,
            "reason": reason,
            "duration_days": duration_days,
            "created_at": datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "exception_id": exception_id,
            "expires_after": f"{duration_days} days",
            "notes": f"Exception applied for: {exception_type}"
        }
    
    @function_tool
    async def escalate_to_manager(
        self,
        context: RunContext_T,
        issue_summary: Annotated[str, Field(description="Summary of the issue requiring manager attention")],
        priority: Annotated[str, Field(description="Priority level (standard, high, urgent)")] = "high",
    ) -> Dict[str, Any]:
        """Escalate an issue to a human manager when it cannot be resolved by AI agents"""
        userdata = context.userdata
        
        # In a real implementation, this would create a ticket and notify a manager
        escalation_id = f"esc_{hash(issue_summary) % 10000}"
        
        # Store the escalation details
        if "escalations" not in userdata.issue_details:
            userdata.issue_details["escalations"] = []
            
        userdata.issue_details["escalations"].append({
            "id": escalation_id,
            "summary": issue_summary,
            "priority": priority,
            "created_at": datetime.now().isoformat()
        })
        
        # Log the escalation for tracking
        logger.info(
            f"Escalated issue to manager: {issue_summary}, "
            f"priority: {priority}, customer: {userdata.customer_id}"
        )
        
        # Calculate expected response time based on priority
        response_times = {
            "standard": "24 hours",
            "high": "4 hours",
            "urgent": "30 minutes"
        }
        
        return {
            "status": "escalated",
            "escalation_id": escalation_id,
            "expected_response": response_times.get(priority, "24 hours"),
            "contact_method": "A manager will contact you directly"
        }
    
    @function_tool
    async def issue_goodwill_credit(
        self,
        context: RunContext_T,
        amount: Annotated[float, Field(description="Amount of credit to issue")],
        reason: Annotated[str, Field(description="Reason for issuing goodwill credit")],
        expiration_days: Annotated[int, Field(description="Number of days until credit expires")] = 90,
    ) -> Dict[str, Any]:
        """Issue a goodwill credit to compensate for negative customer experiences"""
        userdata = context.userdata
        
        # Security check
        if not userdata.verification_status:
            return {
                "status": "failed", 
                "reason": "Customer identity must be verified before issuing credits"
            }
        
        # Check credit amount against authorization limit
        # In a real scenario, this would be based on agent permission levels
        max_credit = 100.0
        if amount > max_credit:
            return {
                "status": "failed",
                "reason": f"Credit amount exceeds authorized limit of ${max_credit}"
            }
        
        # In a real implementation, this would call billing API
        credit_id = f"credit_{hash(f'{userdata.customer_id}_{amount}') % 10000}"
        
        # Store the credit information
        if "credits" not in userdata.issue_details:
            userdata.issue_details["credits"] = []
            
        userdata.issue_details["credits"].append({
            "id": credit_id,
            "amount": amount,
            "reason": reason,
            "expiration_days": expiration_days,
            "created_at": datetime.now().isoformat()
        })
        
        # Log the credit for audit purposes
        logger.info(
            f"Issued goodwill credit of ${amount} to customer {userdata.customer_id}, "
            f"reason: {reason}, expires in {expiration_days} days"
        )
        
        return {
            "status": "success",
            "credit_id": credit_id,
            "amount": amount,
            "expiration": f"{expiration_days} days",
            "notes": f"Credit issued for: {reason}"
        }
    
    @function_tool
    async def create_followup_appointment(
        self,
        context: RunContext_T,
        scheduled_date: Annotated[str, Field(description="ISO format date for the followup (YYYY-MM-DD)")],
        notes: Annotated[str, Field(description="Notes about what needs to be followed up")],
        priority: Annotated[str, Field(description="Priority level (low, medium, high)")] = "medium",
    ) -> Dict[str, Any]:
        """Schedule a follow-up appointment to check on issue resolution progress"""
        userdata = context.userdata
        
        # In a real implementation, this would create a calendar appointment
        appointment_id = f"appt_{hash(f'{userdata.customer_id}_{scheduled_date}') % 10000}"
        
        # Store the appointment information
        if "appointments" not in userdata.issue_details:
            userdata.issue_details["appointments"] = []
            
        userdata.issue_details["appointments"].append({
            "id": appointment_id,
            "scheduled_date": scheduled_date,
            "notes": notes,
            "priority": priority,
            "created_at": datetime.now().isoformat()
        })
        
        # Log the appointment
        logger.info(
            f"Created follow-up appointment for customer {userdata.customer_id} on {scheduled_date}, "
            f"priority: {priority}, notes: {notes}"
        )
        
        return {
            "status": "scheduled",
            "appointment_id": appointment_id,
            "scheduled_date": scheduled_date,
            "confirmation_message": f"Your follow-up has been scheduled for {scheduled_date}"
        }
    
    @function_tool
    async def route_to_greeter(self, context: RunContext_T) -> tuple[Agent, str]:
        """Return to the main greeter agent"""
        return await self._transfer_to_agent("greeter", context) 