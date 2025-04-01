"""
Company model and database operations
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import Company
from utils.logging import get_logger

logger = get_logger(__name__)

async def create_company(
    session: AsyncSession,
    company_id: str,
    name: str,
    email: str,
    tier: str = "basic",
    api_key: str = None,
    status: str = "active"
) -> Company:
    """
    Create a new company
    """
    company = Company(
        id=company_id,
        name=name,
        email=email,
        tier=tier,
        api_key=api_key,
        status=status,
        created_at=datetime.utcnow()
    )
    
    session.add(company)
    await session.commit()
    await session.refresh(company)
    
    logger.info(f"Created company: {company_id}, {name}")
    return company

async def update_company(
    session: AsyncSession,
    company_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    tier: Optional[str] = None,
    api_key: Optional[str] = None,
    status: Optional[str] = None
) -> Company:
    """
    Update an existing company
    """
    # Get the current company
    company = await get_company(session, company_id)
    if not company:
        raise ValueError(f"Company not found: {company_id}")
    
    # Prepare update data with only non-None values
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if email is not None:
        update_data["email"] = email
    if tier is not None:
        update_data["tier"] = tier
    if api_key is not None:
        update_data["api_key"] = api_key
    if status is not None:
        update_data["status"] = status
    
    # Update the company
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await session.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**update_data)
        )
        await session.commit()
    
    # Refresh and return the updated company
    company = await get_company(session, company_id)
    logger.info(f"Updated company: {company_id}")
    return company

async def delete_company(
    session: AsyncSession,
    company_id: str
) -> bool:
    """
    Delete a company
    """
    result = await session.execute(
        delete(Company)
        .where(Company.id == company_id)
    )
    await session.commit()
    
    if result.rowcount > 0:
        logger.info(f"Deleted company: {company_id}")
        return True
    
    logger.warning(f"Company not found for deletion: {company_id}")
    return False

async def get_company(
    session: AsyncSession,
    company_id: str
) -> Optional[Company]:
    """
    Get a company by ID
    """
    result = await session.execute(
        select(Company)
        .where(Company.id == company_id)
    )
    
    company = result.scalars().first()
    return company

async def get_company_by_api_key(
    session: AsyncSession,
    api_key: str
) -> Optional[Company]:
    """
    Get a company by API key
    """
    result = await session.execute(
        select(Company)
        .where(Company.api_key == api_key)
    )
    
    company = result.scalars().first()
    return company

async def list_companies(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> List[Company]:
    """
    List all companies
    """
    result = await session.execute(
        select(Company)
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    companies = result.scalars().all()
    return list(companies) 