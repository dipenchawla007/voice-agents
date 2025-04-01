"""
Notion connector for integrating Notion data with the voice agent platform.

This connector processes Notion pages, databases, and other content, and makes it
available to voice agents for enhanced knowledge access.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from services.integration.data_processor import DataProcessor

logger = logging.getLogger(__name__)

class NotionConnector:
    """Connector for Notion integration."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the Notion connector."""
        self.db = db
        self.data_processor = DataProcessor(db)
    
    async def process_pages(
        self, 
        company_id: str, 
        pages: List[Dict[str, Any]],
        database_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process Notion pages and store them for agent access.
        
        Args:
            company_id: ID of the company
            pages: List of Notion page data
            database_id: Optional Notion database ID for context
            
        Returns:
            Dictionary with processing results
        """
        if not pages:
            return {"pages_processed": 0}
        
        pages_processed = 0
        
        try:
            # Process each page
            for page in pages:
                # Transform the page data to optimize for agent access
                transformed_page = self._transform_page(page, database_id)
                
                # Store in standardized format with notion:pages data type
                result = await self.data_processor.process_company_data(
                    company_id=company_id,
                    data_type="notion:pages",
                    data=transformed_page
                )
                
                pages_processed += 1
            
            return {
                "company_id": company_id,
                "pages_processed": pages_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing Notion pages: {str(e)}")
            # Return partial success information
            return {
                "company_id": company_id,
                "pages_processed": pages_processed,
                "error": str(e)
            }
    
    async def process_database(
        self, 
        company_id: str, 
        database: Dict[str, Any],
        include_pages: bool = False
    ) -> Dict[str, Any]:
        """
        Process Notion database structure and optionally its pages.
        
        Args:
            company_id: ID of the company
            database: Notion database data
            include_pages: Whether to include all database pages
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Transform the database data to optimize for agent access
            transformed_database = self._transform_database(database)
            
            # Store in standardized format with notion:databases data type
            result = await self.data_processor.process_company_data(
                company_id=company_id,
                data_type="notion:databases",
                data=transformed_database
            )
            
            pages_processed = 0
            
            # If include_pages flag is set and pages are provided, process them too
            if include_pages and "pages" in database and isinstance(database["pages"], list):
                database_id = database.get("id")
                pages_result = await self.process_pages(
                    company_id=company_id,
                    pages=database["pages"],
                    database_id=database_id
                )
                pages_processed = pages_result.get("pages_processed", 0)
            
            return {
                "company_id": company_id,
                "database_id": transformed_database.get("id"),
                "pages_processed": pages_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing Notion database: {str(e)}")
            return {
                "company_id": company_id,
                "error": str(e)
            }
    
    def _transform_page(
        self, 
        page: Dict[str, Any],
        database_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transform Notion page data for optimal agent access.
        
        This standardizes the format and extracts content in a way that's
        easier for voice agents to use in conversations.
        """
        # Extract core metadata
        transformed = {
            "id": page.get("id", ""),
            "url": page.get("url", ""),
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
            "archived": page.get("archived", False),
        }
        
        # Associate with database if provided
        if database_id:
            transformed["database_id"] = database_id
        
        # Extract title/name from properties
        properties = page.get("properties", {})
        title = self._extract_title_from_properties(properties)
        if title:
            transformed["title"] = title
        
        # Extract content blocks if available
        if "content" in page and isinstance(page["content"], list):
            transformed["content"] = self._extract_content_from_blocks(page["content"])
        
        # Extract properties in a flattened, simplified format
        extracted_properties = self._extract_properties(properties)
        if extracted_properties:
            transformed["properties"] = extracted_properties
        
        return transformed
    
    def _transform_database(self, database: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Notion database data for optimal agent access.
        """
        # Extract core metadata
        transformed = {
            "id": database.get("id", ""),
            "title": self._extract_title_from_rich_text(database.get("title", [])),
            "url": database.get("url", ""),
            "created_time": database.get("created_time"),
            "last_edited_time": database.get("last_edited_time"),
        }
        
        # Extract database schema (property configurations)
        property_config = {}
        for prop_name, prop_config in database.get("properties", {}).items():
            prop_type = prop_config.get("type")
            property_config[prop_name] = {
                "type": prop_type,
                "id": prop_config.get("id")
            }
            
            # Include additional type-specific schema information
            if prop_type == "select" and "select" in prop_config:
                property_config[prop_name]["options"] = [
                    opt.get("name") for opt in prop_config["select"].get("options", [])
                ]
            elif prop_type == "multi_select" and "multi_select" in prop_config:
                property_config[prop_name]["options"] = [
                    opt.get("name") for opt in prop_config["multi_select"].get("options", [])
                ]
        
        transformed["property_schema"] = property_config
        
        # Extract description if available
        if "description" in database:
            transformed["description"] = self._extract_title_from_rich_text(database.get("description", []))
        
        return transformed
    
    def _extract_title_from_properties(self, properties: Dict[str, Any]) -> str:
        """Extract title from Notion page properties."""
        # Look for common title property names
        for title_key in ["title", "Title", "Name", "name"]:
            if title_key in properties:
                prop = properties[title_key]
                if prop.get("type") == "title" and "title" in prop:
                    return self._extract_title_from_rich_text(prop["title"])
        
        # Fallback to first property that has title type
        for prop_name, prop in properties.items():
            if prop.get("type") == "title" and "title" in prop:
                return self._extract_title_from_rich_text(prop["title"])
                
        return ""
    
    def _extract_title_from_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """Extract plain text from Notion rich text array."""
        if not isinstance(rich_text_array, list):
            return ""
            
        text_parts = []
        for text_obj in rich_text_array:
            if isinstance(text_obj, dict) and "plain_text" in text_obj:
                text_parts.append(text_obj["plain_text"])
            elif isinstance(text_obj, dict) and "text" in text_obj and "content" in text_obj["text"]:
                text_parts.append(text_obj["text"]["content"])
                
        return "".join(text_parts)
    
    def _extract_content_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract content from Notion content blocks."""
        content_parts = []
        
        for block in blocks:
            block_type = block.get("type")
            
            # Handle different block types
            if block_type == "paragraph":
                text = self._extract_title_from_rich_text(block.get("paragraph", {}).get("rich_text", []))
                if text:
                    content_parts.append(text)
                    
            elif block_type == "heading_1":
                text = self._extract_title_from_rich_text(block.get("heading_1", {}).get("rich_text", []))
                if text:
                    content_parts.append(f"# {text}")
                    
            elif block_type == "heading_2":
                text = self._extract_title_from_rich_text(block.get("heading_2", {}).get("rich_text", []))
                if text:
                    content_parts.append(f"## {text}")
                    
            elif block_type == "heading_3":
                text = self._extract_title_from_rich_text(block.get("heading_3", {}).get("rich_text", []))
                if text:
                    content_parts.append(f"### {text}")
                    
            elif block_type == "bulleted_list_item":
                text = self._extract_title_from_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
                if text:
                    content_parts.append(f"• {text}")
                    
            elif block_type == "numbered_list_item":
                text = self._extract_title_from_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
                if text:
                    # We don't handle actual numbering since we're flattening the content
                    content_parts.append(f"- {text}")
                    
            elif block_type == "to_do":
                text = self._extract_title_from_rich_text(block.get("to_do", {}).get("rich_text", []))
                checked = block.get("to_do", {}).get("checked", False)
                checkbox = "☑" if checked else "☐"
                if text:
                    content_parts.append(f"{checkbox} {text}")
                    
            elif block_type == "code":
                code = self._extract_title_from_rich_text(block.get("code", {}).get("rich_text", []))
                language = block.get("code", {}).get("language", "")
                if code:
                    content_parts.append(f"Code ({language}): {code}")
                    
            elif block_type == "quote":
                text = self._extract_title_from_rich_text(block.get("quote", {}).get("rich_text", []))
                if text:
                    content_parts.append(f"> {text}")
                    
            # Recursively process child blocks if available
            if "children" in block and isinstance(block["children"], list):
                child_content = self._extract_content_from_blocks(block["children"])
                if child_content:
                    content_parts.append(child_content)
        
        return "\n\n".join(content_parts)
    
    def _extract_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract properties from Notion page properties."""
        extracted = {}
        
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            
            # Skip title as it's already handled separately
            if prop_type == "title":
                continue
                
            # Handle different property types
            if prop_type == "rich_text":
                extracted[prop_name] = self._extract_title_from_rich_text(prop_data.get("rich_text", []))
                
            elif prop_type == "number":
                extracted[prop_name] = prop_data.get("number")
                
            elif prop_type == "select":
                select_obj = prop_data.get("select")
                if select_obj and "name" in select_obj:
                    extracted[prop_name] = select_obj["name"]
                    
            elif prop_type == "multi_select":
                multi_select = prop_data.get("multi_select", [])
                extracted[prop_name] = [item.get("name") for item in multi_select if "name" in item]
                
            elif prop_type == "date":
                date_obj = prop_data.get("date")
                if date_obj and "start" in date_obj:
                    date_str = date_obj["start"]
                    if "end" in date_obj and date_obj["end"]:
                        date_str += f" to {date_obj['end']}"
                    extracted[prop_name] = date_str
                    
            elif prop_type == "checkbox":
                extracted[prop_name] = prop_data.get("checkbox", False)
                
            elif prop_type == "url":
                extracted[prop_name] = prop_data.get("url")
                
            elif prop_type == "email":
                extracted[prop_name] = prop_data.get("email")
                
            elif prop_type == "phone_number":
                extracted[prop_name] = prop_data.get("phone_number")
                
            elif prop_type == "formula":
                formula = prop_data.get("formula", {})
                formula_type = formula.get("type")
                if formula_type:
                    extracted[prop_name] = formula.get(formula_type)
        
        return extracted 