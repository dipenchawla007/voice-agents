"""
API routes for external data integration.

These endpoints allow companies to sync their data with the voice agent platform.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from db.session import get_db
from models.company import Company
from services.company.key_manager import CompanyKeyManager
from services.integration.data_processor import DataProcessor
from services.integration.connectors.zendesk import ZendeskConnector
from services.integration.connectors.notion import NotionConnector

router = APIRouter(prefix="/api/v1/integration", tags=["integration"])

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def validate_company_api_key(
    api_key: str = Depends(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db)
):
    """Validate the company API key and return the company."""
    key_manager = CompanyKeyManager(db)
    company = await key_manager.validate_api_key(api_key)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return company

@router.post("/data/sync")
async def sync_company_data(
    data: Dict[str, Any] = Body(...),
    data_type: str = Query(..., description="Type of data being synced (customers, products, tickets, etc.)"),
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync company data to the voice agent platform.
    
    Companies can use this endpoint to push their data for agent access.
    """
    try:
        processor = DataProcessor(db)
        result = await processor.process_company_data(
            company_id=company.id,
            data_type=data_type,
            data=data
        )
        return {
            "success": True,
            "message": f"Successfully processed {data_type} data",
            "records_processed": result.get("records_processed", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@router.post("/data/batch")
async def batch_sync_company_data(
    batch_data: List[Dict[str, Any]] = Body(...),
    data_type: str = Query(..., description="Type of data being synced"),
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch sync multiple records of company data.
    
    Optimized for large data transfers with reduced API calls.
    """
    try:
        processor = DataProcessor(db)
        result = await processor.process_batch_data(
            company_id=company.id,
            data_type=data_type,
            batch_data=batch_data
        )
        return {
            "success": True,
            "message": f"Successfully processed batch {data_type} data",
            "batch_size": len(batch_data),
            "records_processed": result.get("records_processed", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing batch data: {str(e)}")

@router.delete("/data/{data_type}")
async def delete_company_data(
    data_type: str = Path(..., description="Type of data to delete"),
    record_ids: List[str] = Body(..., description="List of record IDs to delete"),
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete company data from the voice agent platform.
    
    Companies can remove data that should no longer be accessible to agents.
    """
    try:
        processor = DataProcessor(db)
        result = await processor.delete_company_data(
            company_id=company.id,
            data_type=data_type,
            record_ids=record_ids
        )
        return {
            "success": True,
            "message": f"Successfully deleted {data_type} data",
            "records_deleted": result.get("records_deleted", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting data: {str(e)}")

# Zendesk Integration

@router.post("/zendesk/tickets")
async def sync_zendesk_tickets(
    ticket_data: List[Dict[str, Any]] = Body(...),
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync Zendesk tickets with the voice agent platform.
    
    Specialized endpoint optimized for Zendesk ticket data structure.
    """
    try:
        zendesk = ZendeskConnector(db)
        result = await zendesk.process_tickets(
            company_id=company.id,
            tickets=ticket_data
        )
        return {
            "success": True,
            "message": "Successfully processed Zendesk tickets",
            "tickets_processed": result.get("tickets_processed", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Zendesk tickets: {str(e)}")

@router.post("/zendesk/users")
async def sync_zendesk_users(
    user_data: List[Dict[str, Any]] = Body(...),
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync Zendesk users with the voice agent platform.
    
    Specialized endpoint optimized for Zendesk user data structure.
    """
    try:
        zendesk = ZendeskConnector(db)
        result = await zendesk.process_users(
            company_id=company.id,
            users=user_data
        )
        return {
            "success": True,
            "message": "Successfully processed Zendesk users",
            "users_processed": result.get("users_processed", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Zendesk users: {str(e)}")

# Notion Integration

@router.post("/notion/pages")
async def sync_notion_pages(
    page_data: List[Dict[str, Any]] = Body(...),
    database_id: Optional[str] = Query(None, description="Notion database ID for context"),
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync Notion pages with the voice agent platform.
    
    Specialized endpoint optimized for Notion page data structure.
    """
    try:
        notion = NotionConnector(db)
        result = await notion.process_pages(
            company_id=company.id,
            pages=page_data,
            database_id=database_id
        )
        return {
            "success": True,
            "message": "Successfully processed Notion pages",
            "pages_processed": result.get("pages_processed", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Notion pages: {str(e)}")

@router.post("/notion/databases")
async def sync_notion_databases(
    database_data: Dict[str, Any] = Body(...),
    include_pages: bool = Query(False, description="Whether to include all database pages"),
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync Notion database structure with the voice agent platform.
    
    Allows companies to register Notion databases for context.
    """
    try:
        notion = NotionConnector(db)
        result = await notion.process_database(
            company_id=company.id,
            database=database_data,
            include_pages=include_pages
        )
        return {
            "success": True,
            "message": "Successfully processed Notion database",
            "database_id": result.get("database_id"),
            "pages_processed": result.get("pages_processed", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Notion database: {str(e)}")

# Health check and status endpoints

@router.get("/status")
async def integration_status(
    company: Company = Depends(validate_company_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get integration status for the company.
    
    Returns information about connected data sources and sync status.
    """
    processor = DataProcessor(db)
    status = await processor.get_integration_status(company.id)
    
    return {
        "company_id": company.id,
        "connected_sources": status.get("connected_sources", []),
        "last_sync_timestamp": status.get("last_sync_timestamp"),
        "data_types": status.get("data_types", []),
        "record_counts": status.get("record_counts", {}),
        "status": "active"
    } 