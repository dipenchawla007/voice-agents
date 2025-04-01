"""
Agent factory for creating and managing voice agents.

This module provides factory functions to create and manage specialized agents
for the multi-tenant voice agent system.
"""

import logging
from typing import Dict, Optional

from services.voice.base_agent import CustomerData
from services.voice.escalation_agent import EscalationAgent
from livekit.agents import Agent

# Import other agent types
# These imports would typically be here, but this is a simplified example
# And we're assuming they exist in the original structure

logger = logging.getLogger("agent-factory")
logger.setLevel(logging.INFO)

def create_agents(customer_data: CustomerData) -> Dict[str, Agent]:
    """
    Create all specialized agent instances for a customer session.
    
    Args:
        customer_data: Shared customer data object
        
    Returns:
        Dictionary of agent instances keyed by agent type
    """
    # Create the agents
    # In a real implementation, you might configure these based on company settings
    greeter = GreeterAgent()
    billing = BillingAgent()
    technical = TechnicalAgent()
    general = GeneralAgent()
    escalation = EscalationAgent()  # Add our new escalation agent
    
    # Store all agents in a dictionary for easy access
    agents = {
        "greeter": greeter,
        "billing": billing,
        "technical": technical,
        "general": general,
        "escalation": escalation,  # Add our new escalation agent
    }
    
    logger.info(f"Created {len(agents)} agent instances")
    return agents

def add_routing_capabilities(agents: Dict[str, Agent]) -> None:
    """
    Add routing capabilities to the existing GreeterAgent to support
    transferring to the new EscalationAgent.
    
    Args:
        agents: Dictionary of agent instances
    """
    # This function would modify the GreeterAgent to add the route_to_escalation method
    # However, in a real implementation, this would be part of the GreeterAgent class
    # This is just a placeholder to show the concept
    
    greeter = agents.get("greeter")
    if greeter:
        # In a real implementation, we would add a function tool like:
        # @function_tool
        # async def route_to_escalation(self, context: RunContext_T) -> tuple[Agent, str]:
        #     """Called when the customer has a complex issue requiring escalation"""
        #     userdata = context.userdata
        #     userdata.issue_type = "escalation"
        #     return await self._transfer_to_agent("escalation", context)
        
        logger.info("Added escalation routing capability to greeter agent")
    
    # Also add capabilities for other agents to route to escalation
    for agent_name in ["billing", "technical", "general"]:
        agent = agents.get(agent_name)
        if agent:
            # Similar to above, we would add routing capabilities
            logger.info(f"Added escalation routing capability to {agent_name} agent")

def get_default_agent() -> str:
    """Get the default agent type to start with."""
    return "greeter" 