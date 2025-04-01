"""
Quota management service for enforcing usage limits per company
"""
import math
import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.schemas import Company
from services.usage_tracking.tracker import usage_tracker

logger = logging.getLogger(__name__)

class QuotaManager:
    """
    Service for enforcing usage quotas and limits across companies
    Used to prevent overuse and ensure fair resource allocation
    """
    
    async def check_session_quota(
        self,
        session: AsyncSession,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Check if a company has exceeded its session quota
        
        Args:
            session: Database session
            company_id: Company identifier
            
        Returns:
            Dictionary with quota information and whether usage is allowed
        """
        # Get company quotas
        company = await self._get_company(session, company_id)
        if not company:
            logger.warning(f"Quota check failed: Company {company_id} not found")
            return {
                "allowed": False,
                "reason": "Company not found"
            }
        
        # Check company status
        if company.status != "active":
            logger.warning(f"Quota check failed: Company {company_id} is not active")
            return {
                "allowed": False,
                "reason": f"Company status is {company.status}"
            }
        
        # Get current month usage
        current_usage = await usage_tracker.get_current_month_usage(session, company_id)
        
        # Check against quotas
        result = {
            "allowed": True,
            "quotas": {},
            "usage": {}
        }
        
        # Check interaction limit
        max_interactions = company.quotas.get("max_interactions_per_month", 0)
        if max_interactions > 0 and current_usage["total_interactions"] >= max_interactions:
            result["allowed"] = False
            result["quotas"]["interactions"] = {
                "allowed": max_interactions,
                "used": current_usage["total_interactions"],
                "percentage": (current_usage["total_interactions"] / max_interactions) * 100,
                "exceeded": True
            }
        elif max_interactions > 0:
            result["quotas"]["interactions"] = {
                "allowed": max_interactions,
                "used": current_usage["total_interactions"],
                "percentage": (current_usage["total_interactions"] / max_interactions) * 100,
                "exceeded": False
            }
        
        # Check minutes limit
        max_minutes = company.quotas.get("max_minutes_per_month", 0)
        current_minutes = math.ceil(current_usage["total_duration_ms"] / 60000)
        
        if max_minutes > 0 and current_minutes >= max_minutes:
            result["allowed"] = False
            result["quotas"]["minutes"] = {
                "allowed": max_minutes,
                "used": current_minutes,
                "percentage": (current_minutes / max_minutes) * 100,
                "exceeded": True
            }
        elif max_minutes > 0:
            result["quotas"]["minutes"] = {
                "allowed": max_minutes,
                "used": current_minutes,
                "percentage": (current_minutes / max_minutes) * 100,
                "exceeded": False
            }
        
        # Check concurrent sessions
        max_concurrent = company.quotas.get("max_concurrent_sessions", 0)
        current_concurrent = current_usage.get("peak_concurrent_sessions", 0)
        
        if max_concurrent > 0 and current_concurrent >= max_concurrent:
            result["allowed"] = False
            result["quotas"]["concurrent_sessions"] = {
                "allowed": max_concurrent,
                "used": current_concurrent,
                "percentage": (current_concurrent / max_concurrent) * 100,
                "exceeded": True
            }
        elif max_concurrent > 0:
            result["quotas"]["concurrent_sessions"] = {
                "allowed": max_concurrent,
                "used": current_concurrent,
                "percentage": (current_concurrent / max_concurrent) * 100,
                "exceeded": False
            }
        
        # Add usage summary
        result["usage"] = {
            "total_interactions": current_usage["total_interactions"],
            "total_minutes": current_minutes,
            "peak_concurrent_sessions": current_concurrent
        }
        
        # Add overall status
        if not result["allowed"]:
            exceeded_quotas = [
                name for name, quota in result["quotas"].items() 
                if quota.get("exceeded", False)
            ]
            result["reason"] = f"Quota exceeded for: {', '.join(exceeded_quotas)}"
            logger.warning(f"Quota check failed for company {company_id}: {result['reason']}")
        
        return result
    
    async def check_agent_quota(
        self,
        session: AsyncSession,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Check if a company has exceeded its agent quota
        Used when creating new agents
        
        Args:
            session: Database session
            company_id: Company identifier
            
        Returns:
            Dictionary with quota information and whether creation is allowed
        """
        # Get company quotas
        company = await self._get_company(session, company_id)
        if not company:
            return {
                "allowed": False,
                "reason": "Company not found"
            }
        
        # Check company status
        if company.status != "active":
            return {
                "allowed": False,
                "reason": f"Company status is {company.status}"
            }
        
        # Get current agent count
        agent_count = len(company.agents)
        max_agents = company.quotas.get("max_agents", 0)
        
        if max_agents > 0 and agent_count >= max_agents:
            return {
                "allowed": False,
                "reason": "Maximum agent limit reached",
                "quota": {
                    "allowed": max_agents,
                    "used": agent_count,
                    "percentage": (agent_count / max_agents) * 100
                }
            }
        
        return {
            "allowed": True,
            "quota": {
                "allowed": max_agents,
                "used": agent_count,
                "percentage": (agent_count / max_agents) * 100 if max_agents > 0 else 0
            }
        }
    
    async def check_knowledge_base_quota(
        self,
        session: AsyncSession,
        company_id: str,
        file_size_mb: float
    ) -> Dict[str, Any]:
        """
        Check if a company can add a knowledge base file of the given size
        
        Args:
            session: Database session
            company_id: Company identifier
            file_size_mb: Size of the file in megabytes
            
        Returns:
            Dictionary with quota information and whether upload is allowed
        """
        # Get company quotas
        company = await self._get_company(session, company_id)
        if not company:
            return {
                "allowed": False,
                "reason": "Company not found"
            }
        
        # Check company status
        if company.status != "active":
            return {
                "allowed": False,
                "reason": f"Company status is {company.status}"
            }
        
        # Calculate current knowledge base size
        # This is a simplified calculation - would need to be expanded in a real implementation
        current_size_mb = 0
        for agent in company.agents:
            for source in agent.knowledge_sources:
                current_size_mb += source.file_size / (1024 * 1024)  # Convert bytes to MB
        
        max_size_mb = company.quotas.get("max_knowledge_base_size_mb", 0)
        new_total_size = current_size_mb + file_size_mb
        
        if max_size_mb > 0 and new_total_size > max_size_mb:
            return {
                "allowed": False,
                "reason": "Knowledge base size quota exceeded",
                "quota": {
                    "allowed": max_size_mb,
                    "used": current_size_mb,
                    "new_total": new_total_size,
                    "percentage": (new_total_size / max_size_mb) * 100
                }
            }
        
        return {
            "allowed": True,
            "quota": {
                "allowed": max_size_mb,
                "used": current_size_mb,
                "new_total": new_total_size,
                "percentage": (new_total_size / max_size_mb) * 100 if max_size_mb > 0 else 0
            }
        }
    
    async def _get_company(
        self,
        session: AsyncSession,
        company_id: str
    ) -> Optional[Company]:
        """Helper method to get company with quotas"""
        stmt = select(Company).where(Company.id == company_id)
        result = await session.execute(stmt)
        return result.scalars().first()

# Create a singleton instance
quota_manager = QuotaManager() 