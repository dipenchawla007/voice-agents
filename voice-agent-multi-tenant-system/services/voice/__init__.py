"""
Voice agent services package.

This package provides the voice agent system built with LiveKit Agents SDK,
including specialized agents for different customer support scenarios.
"""

from services.voice.base_agent import BaseAgent, CustomerData, VOICES
from services.voice.escalation_agent import EscalationAgent
from services.voice.agent_factory import create_agents, add_routing_capabilities, get_default_agent

__all__ = [
    "BaseAgent",
    "CustomerData", 
    "VOICES",
    "EscalationAgent",
    "create_agents",
    "add_routing_capabilities",
    "get_default_agent"
] 