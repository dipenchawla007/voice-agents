"""
API routes for company management
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import async_session
from models.company import get_company_by_api_key, create_company, update_company, get_company, list_companies
from services.company_key_manager import company_key_manager
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

async def get_db():
    """Dependency for database session"""
    async with async_session() as session:
        yield session

async def validate_admin_api_key(x_api_key: Optional[str] = Header(None)):
    """Validate admin API key"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    
    # In a real system, you'd validate the admin API key against a stored value
    # For now, we'll use a simple check
    admin_key = "ADMIN_API_KEY"  # This should come from config/env
    if x_api_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    
    return x_api_key

@router.post("/", response_model=Dict[str, Any])
async def create_new_company(
    request: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    api_key: str = Depends(validate_admin_api_key)
):
    """
    Create a new company
    
    Required request body:
    - name: Company name
    - email: Admin email
    - tier: Subscription tier (basic, pro, enterprise)
    
    Returns:
        Company data including API key
    """
    # Validate required fields
    name = request.get("name")
    email = request.get("email")
    tier = request.get("tier", "basic")
    
    if not name or not email:
        raise HTTPException(status_code=400, detail="Name and email are required")
    
    # Create company
    try:
        # Generate a unique company ID
        company_id = str(uuid4())
        
        # Generate API key
        api_key = company_key_manager.generate_api_key(company_id)
        
        # Create company in DB
        company = await create_company(
            session,
            company_id=company_id,
            name=name,
            email=email, 
            tier=tier,
            api_key=api_key
        )
        
        logger.info(f"Created new company: {company_id}, {name}")
        
        # Return company data
        return {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "tier": company.tier,
            "api_key": api_key,
            "created_at": company.created_at,
            "status": company.status
        }
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating company: {str(e)}")

@router.get("/", response_model=List[Dict[str, Any]])
async def get_companies(
    session: AsyncSession = Depends(get_db),
    api_key: str = Depends(validate_admin_api_key),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List companies (admin only)
    
    Returns:
        List of companies
    """
    try:
        companies = await list_companies(session, limit=limit, offset=offset)
        
        # Format response
        result = []
        for company in companies:
            result.append({
                "id": company.id,
                "name": company.name,
                "email": company.email,
                "tier": company.tier,
                "created_at": company.created_at,
                "status": company.status
            })
        
        return result
    except Exception as e:
        logger.error(f"Error listing companies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing companies: {str(e)}")

@router.get("/{company_id}", response_model=Dict[str, Any])
async def get_company_details(
    company_id: str = Path(..., description="Company ID"),
    session: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get company details
    
    Returns:
        Company data
    """
    # Validate API key
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    
    # Check if admin key or company key
    is_admin = False
    try:
        api_key = await validate_admin_api_key(x_api_key)
        is_admin = True
    except HTTPException:
        # Not an admin key, check if it's a valid company key
        company = await get_company_by_api_key(session, x_api_key)
        if not company:
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        # Company can only access its own data
        if company.id != company_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get company data
    try:
        company = await get_company(session, company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Return company data
        return {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "tier": company.tier,
            "created_at": company.created_at,
            "status": company.status,
            # Only include sensitive data for admins
            "api_key": company.api_key if is_admin else None
        }
    except Exception as e:
        logger.error(f"Error getting company details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting company details: {str(e)}")

@router.put("/{company_id}", response_model=Dict[str, Any])
async def update_company_details(
    request: Dict[str, Any],
    company_id: str = Path(..., description="Company ID"),
    session: AsyncSession = Depends(get_db),
    api_key: str = Depends(validate_admin_api_key)
):
    """
    Update company details (admin only)
    
    Request body can include:
    - name: Company name
    - email: Admin email
    - tier: Subscription tier
    - status: Company status (active, suspended)
    
    Returns:
        Updated company data
    """
    # Validate company exists
    company = await get_company(session, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update company
    try:
        updated_company = await update_company(
            session,
            company_id=company_id,
            name=request.get("name"),
            email=request.get("email"),
            tier=request.get("tier"),
            status=request.get("status")
        )
        
        logger.info(f"Updated company: {company_id}")
        
        # Return updated company data
        return {
            "id": updated_company.id,
            "name": updated_company.name,
            "email": updated_company.email,
            "tier": updated_company.tier,
            "created_at": updated_company.created_at,
            "status": updated_company.status
        }
    except Exception as e:
        logger.error(f"Error updating company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating company: {str(e)}")

@router.post("/{company_id}/reset-key", response_model=Dict[str, Any])
async def reset_api_key(
    company_id: str = Path(..., description="Company ID"),
    session: AsyncSession = Depends(get_db),
    api_key: str = Depends(validate_admin_api_key)
):
    """
    Reset a company's API key (admin only)
    
    Returns:
        New API key
    """
    # Validate company exists
    company = await get_company(session, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Generate new API key
    try:
        new_api_key = company_key_manager.generate_api_key(company_id)
        
        # Update company with new API key
        updated_company = await update_company(
            session,
            company_id=company_id,
            api_key=new_api_key
        )
        
        logger.info(f"Reset API key for company: {company_id}")
        
        # Return new API key
        return {
            "company_id": company_id,
            "api_key": new_api_key
        }
    except Exception as e:
        logger.error(f"Error resetting API key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resetting API key: {str(e)}") 