"""
Base agent class and shared utilities for voice agents.

This module provides the foundation for all specialized voice agents
in the multi-tenant voice agent system using LiveKit Agents SDK.
"""

import logging
from typing import Annotated, Optional, Dict, List, Any, Union
from dataclasses import dataclass, field

from livekit.agents import Agent, RunContext
from livekit.agents.llm import ChatItem

# Set up logging
logger = logging.getLogger("base-agent")
logger.setLevel(logging.INFO)

# Define appropriate voices for different agents
VOICES = {
    "greeter": "nova",
    "billing": "onyx",
    "technical": "alloy",
    "general": "echo",
    "escalation": "alloy",  # Using alloy for escalation agent
}

@dataclass
class CustomerData:
    """Shared data structure for customer information across agents"""
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    
    issue_type: Optional[str] = None
    issue_details: Dict[str, Any] = field(default_factory=dict)
    
    verification_status: Optional[bool] = False
    
    order_id: Optional[str] = None
    order_details: Optional[Dict[str, Any]] = None
    
    ticket_id: Optional[str] = None
    
    agents: Dict[str, Agent] = field(default_factory=dict)
    prev_agent: Optional[Agent] = None
    
    def summarize(self) -> str:
        """Generate a summary of customer data for agent context"""
        summary = {
            "customer_id": self.customer_id or "unknown",
            "customer_name": self.customer_name or "unknown",
            "verification_status": self.verification_status,
            "issue_type": self.issue_type or "unknown",
            "issue_details": self.issue_details or {},
        }
        
        # Only include necessary details for specific issue types
        if self.issue_type == "billing" and self.order_id:
            summary["order_id"] = self.order_id
            summary["order_details"] = self.order_details
        
        if self.issue_type == "technical" and self.ticket_id:
            summary["ticket_id"] = self.ticket_id
        
        return str(summary)


# Type alias for our specific RunContext
RunContext_T = RunContext[CustomerData]


class BaseAgent(Agent):
    """Base agent with shared functionality for all specialized agents"""
    
    async def on_enter(self) -> None:
        """Called when the agent becomes active"""
        agent_name = self.__class__.__name__
        logger.info(f"Entering {agent_name} agent")
        
        userdata: CustomerData = self.session.userdata
        chat_ctx = self.chat_ctx.copy()
        
        # Transfer context from previous agent if exists
        if userdata.prev_agent:
            items_copy = self._truncate_chat_ctx(
                userdata.prev_agent.chat_ctx.items, 
                keep_function_call=True
            )
            existing_ids = {item.id for item in chat_ctx.items}
            items_copy = [item for item in items_copy if item.id not in existing_ids]
            chat_ctx.items.extend(items_copy)
        
        # Add system message with current customer data
        chat_ctx.add_message(
            role="system",
            content=f"You are {agent_name}, a customer support agent. Current customer data: {userdata.summarize()}"
        )
        
        await self.update_chat_ctx(chat_ctx)
        self.session.generate_reply(tool_choice="none")
    
    async def _transfer_to_agent(self, name: str, context: RunContext_T) -> tuple[Agent, str]:
        """Transfer the conversation to another specialized agent"""
        userdata = context.userdata
        current_agent = context.session.current_agent
        next_agent = userdata.agents[name]
        userdata.prev_agent = current_agent
        
        transfer_reason = f"Transferring to {name} specialist."
        logger.info(f"Transferring from {current_agent.__class__.__name__} to {name}")
        
        return next_agent, transfer_reason
    
    def _truncate_chat_ctx(
        self,
        items: list[ChatItem],
        keep_last_n_messages: int = 6,
        keep_system_message: bool = False,
        keep_function_call: bool = False,
    ) -> list[ChatItem]:
        """Truncate chat context to manage token usage"""
        
        def _valid_item(item: ChatItem) -> bool:
            if not keep_system_message and item.type == "message" and item.role == "system":
                return False
            if not keep_function_call and item.type in [
                "function_call",
                "function_call_output",
            ]:
                return False
            return True
        
        new_items: list[ChatItem] = []
        for item in reversed(items):
            if _valid_item(item):
                new_items.append(item)
            if len(new_items) >= keep_last_n_messages:
                break
        new_items = new_items[::-1]
        
        # Ensure we don't start with function call items
        while new_items and new_items[0].type in ["function_call", "function_call_output"]:
            new_items.pop(0)
        
        return new_items 