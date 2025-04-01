"""
Zendesk connector for integrating Zendesk data with the voice agent platform.

This connector processes Zendesk tickets, users, and other data, and makes it
available to voice agents for customer support scenarios.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from services.integration.data_processor import DataProcessor

logger = logging.getLogger(__name__)

class ZendeskConnector:
    """Connector for Zendesk integration."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the Zendesk connector."""
        self.db = db
        self.data_processor = DataProcessor(db)
    
    async def process_tickets(
        self, 
        company_id: str, 
        tickets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process Zendesk tickets and store them for agent access.
        
        Args:
            company_id: ID of the company
            tickets: List of Zendesk ticket data
            
        Returns:
            Dictionary with processing results
        """
        if not tickets:
            return {"tickets_processed": 0}
        
        tickets_processed = 0
        
        try:
            # Process each ticket
            for ticket in tickets:
                # Transform the ticket data to optimize for agent access
                transformed_ticket = self._transform_ticket(ticket)
                
                # Store in standardized format with zendesk:tickets data type
                result = await self.data_processor.process_company_data(
                    company_id=company_id,
                    data_type="zendesk:tickets",
                    data=transformed_ticket
                )
                
                tickets_processed += 1
            
            return {
                "company_id": company_id,
                "tickets_processed": tickets_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing Zendesk tickets: {str(e)}")
            # Return partial success information
            return {
                "company_id": company_id,
                "tickets_processed": tickets_processed,
                "error": str(e)
            }
    
    async def process_users(
        self, 
        company_id: str, 
        users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process Zendesk users and store them for agent access.
        
        Args:
            company_id: ID of the company
            users: List of Zendesk user data
            
        Returns:
            Dictionary with processing results
        """
        if not users:
            return {"users_processed": 0}
        
        users_processed = 0
        
        try:
            # Process each user
            for user in users:
                # Transform the user data to optimize for agent access
                transformed_user = self._transform_user(user)
                
                # Store in standardized format with zendesk:users data type
                result = await self.data_processor.process_company_data(
                    company_id=company_id,
                    data_type="zendesk:users",
                    data=transformed_user
                )
                
                users_processed += 1
            
            return {
                "company_id": company_id,
                "users_processed": users_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing Zendesk users: {str(e)}")
            # Return partial success information
            return {
                "company_id": company_id,
                "users_processed": users_processed,
                "error": str(e)
            }
    
    def _transform_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Zendesk ticket data for optimal agent access.
        
        This standardizes the format and optimizes the structure for
        voice agent interactions.
        """
        # Extract the most relevant fields
        transformed = {
            "id": str(ticket.get("id")),
            "subject": ticket.get("subject", ""),
            "description": ticket.get("description", ""),
            "status": ticket.get("status", ""),
            "priority": ticket.get("priority", ""),
            "created_at": ticket.get("created_at"),
            "updated_at": ticket.get("updated_at"),
            "requester_id": str(ticket.get("requester_id")) if ticket.get("requester_id") else None,
            "assignee_id": str(ticket.get("assignee_id")) if ticket.get("assignee_id") else None,
            "tags": ticket.get("tags", []),
        }
        
        # Extract and transform comments if available
        if "comments" in ticket and isinstance(ticket["comments"], list):
            transformed["comments"] = []
            for comment in ticket["comments"]:
                transformed_comment = {
                    "id": str(comment.get("id")),
                    "author_id": str(comment.get("author_id")) if comment.get("author_id") else None,
                    "body": comment.get("body", ""),
                    "html_body": comment.get("html_body", ""),
                    "public": comment.get("public", True),
                    "created_at": comment.get("created_at"),
                }
                transformed["comments"].append(transformed_comment)
        
        # Extract custom fields if available
        if "custom_fields" in ticket and isinstance(ticket["custom_fields"], list):
            custom_fields = {}
            for field in ticket["custom_fields"]:
                if "id" in field and "value" in field:
                    custom_fields[str(field["id"])] = field["value"]
            transformed["custom_fields"] = custom_fields
        
        return transformed
    
    def _transform_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Zendesk user data for optimal agent access.
        
        This standardizes the format and optimizes the structure for
        voice agent interactions.
        """
        # Extract the most relevant fields
        transformed = {
            "id": str(user.get("id")),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "role": user.get("role", ""),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
            "time_zone": user.get("time_zone"),
            "locale": user.get("locale"),
            "active": user.get("active", True),
            "tags": user.get("tags", []),
        }
        
        # Extract custom user fields if available
        if "user_fields" in user and isinstance(user["user_fields"], dict):
            transformed["user_fields"] = user["user_fields"]
        
        return transformed 