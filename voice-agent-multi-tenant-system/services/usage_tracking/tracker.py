"""
Usage tracking service for monitoring agent interactions across companies
"""
import uuid
import logging
import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from db.schemas import Usage, DailyUsage, Company

logger = logging.getLogger(__name__)

class UsageTracker:
    """
    Service for tracking and aggregating usage metrics across companies
    Used for billing, quota enforcement, and analytics
    """
    
    async def track_session(
        self,
        session: AsyncSession,
        session_data: Dict[str, Any]
    ) -> str:
        """
        Record a session for tracking and billing purposes
        
        Args:
            session: Database session
            session_data: Session data containing:
                - company_id: Company identifier
                - agent_id: Agent identifier
                - user_id: User identifier (optional)
                - duration_ms: Session duration in milliseconds
                - tokens_used: Number of tokens used (optional)
                - interaction_count: Number of interactions (optional)
                
        Returns:
            ID of the created usage record
        """
        # Validate required fields
        required_fields = ["company_id", "agent_id", "duration_ms"]
        for field in required_fields:
            if field not in session_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Create usage record
        record_id = str(uuid.uuid4())
        usage_record = Usage(
            id=record_id,
            company_id=session_data["company_id"],
            agent_id=session_data["agent_id"],
            user_id=session_data.get("user_id"),
            session_id=session_data.get("session_id", str(uuid.uuid4())),
            timestamp=session_data.get("timestamp", datetime.datetime.now()),
            duration_ms=session_data["duration_ms"],
            tokens_used=session_data.get("tokens_used", 0),
            interaction_count=session_data.get("interaction_count", 0)
        )
        
        # Add to database
        session.add(usage_record)
        await session.commit()
        
        # Update aggregates
        await self.update_daily_aggregates(
            session, 
            session_data["company_id"], 
            session_data["agent_id"],
            record_id
        )
        
        logger.info(f"Tracked session for company {session_data['company_id']}, agent {session_data['agent_id']}")
        return record_id
    
    async def update_daily_aggregates(
        self,
        session: AsyncSession,
        company_id: str,
        agent_id: str,
        usage_record_id: Optional[str] = None
    ) -> None:
        """
        Update daily usage aggregates for a company and agent
        
        Args:
            session: Database session
            company_id: Company identifier
            agent_id: Agent identifier
            usage_record_id: Optional ID of the specific usage record to incorporate
        """
        # Get the current date (truncated to day)
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if aggregate record exists for today
        stmt = select(DailyUsage).where(
            DailyUsage.company_id == company_id,
            DailyUsage.agent_id == agent_id,
            func.date(DailyUsage.date) == today.date()
        )
        result = await session.execute(stmt)
        daily_record = result.scalars().first()
        
        if daily_record:
            # Update existing record
            # Calculate new aggregates from raw usage data
            total_interactions, total_duration, total_tokens, unique_users = \
                await self._calculate_daily_totals(session, company_id, agent_id, today)
            
            daily_record.total_interactions = total_interactions
            daily_record.total_duration_ms = total_duration
            daily_record.total_tokens = total_tokens
            daily_record.unique_users = unique_users
            
            # Update peak concurrent sessions if needed
            current_concurrent = await self._get_current_concurrent_sessions(session, company_id)
            if current_concurrent > daily_record.peak_concurrent_sessions:
                daily_record.peak_concurrent_sessions = current_concurrent
                
            await session.commit()
            logger.debug(f"Updated daily usage record for company {company_id}, agent {agent_id}")
        else:
            # Create new record
            record_id = str(uuid.uuid4())
            
            # Calculate totals
            total_interactions, total_duration, total_tokens, unique_users = \
                await self._calculate_daily_totals(session, company_id, agent_id, today)
            
            current_concurrent = await self._get_current_concurrent_sessions(session, company_id)
            
            new_daily = DailyUsage(
                id=record_id,
                company_id=company_id,
                agent_id=agent_id,
                date=today,
                total_interactions=total_interactions,
                total_duration_ms=total_duration,
                total_tokens=total_tokens,
                unique_users=unique_users,
                peak_concurrent_sessions=current_concurrent
            )
            
            session.add(new_daily)
            await session.commit()
            logger.debug(f"Created new daily usage record for company {company_id}, agent {agent_id}")
    
    async def _calculate_daily_totals(
        self,
        session: AsyncSession,
        company_id: str,
        agent_id: str,
        date: datetime.datetime
    ) -> tuple[int, int, int, int]:
        """
        Calculate daily totals from raw usage data
        
        Returns:
            Tuple of (total_interactions, total_duration_ms, total_tokens, unique_users)
        """
        # Get start and end of day
        start_of_day = date
        end_of_day = date + datetime.timedelta(days=1)
        
        # Get total interactions
        interactions_stmt = select(func.sum(Usage.interaction_count)).where(
            Usage.company_id == company_id,
            Usage.agent_id == agent_id,
            Usage.timestamp >= start_of_day,
            Usage.timestamp < end_of_day
        )
        interactions_result = await session.execute(interactions_stmt)
        total_interactions = interactions_result.scalar() or 0
        
        # Get total duration
        duration_stmt = select(func.sum(Usage.duration_ms)).where(
            Usage.company_id == company_id,
            Usage.agent_id == agent_id,
            Usage.timestamp >= start_of_day,
            Usage.timestamp < end_of_day
        )
        duration_result = await session.execute(duration_stmt)
        total_duration = duration_result.scalar() or 0
        
        # Get total tokens
        tokens_stmt = select(func.sum(Usage.tokens_used)).where(
            Usage.company_id == company_id,
            Usage.agent_id == agent_id,
            Usage.timestamp >= start_of_day,
            Usage.timestamp < end_of_day
        )
        tokens_result = await session.execute(tokens_stmt)
        total_tokens = tokens_result.scalar() or 0
        
        # Get unique users
        users_stmt = select(func.count(func.distinct(Usage.user_id))).where(
            Usage.company_id == company_id,
            Usage.agent_id == agent_id,
            Usage.timestamp >= start_of_day,
            Usage.timestamp < end_of_day,
            Usage.user_id != None  # Exclude null user_ids
        )
        users_result = await session.execute(users_stmt)
        unique_users = users_result.scalar() or 0
        
        return total_interactions, total_duration, total_tokens, unique_users
    
    async def _get_current_concurrent_sessions(
        self,
        session: AsyncSession,
        company_id: str
    ) -> int:
        """
        Get the current number of concurrent sessions for a company
        This is a placeholder - in a real implementation this would query
        LiveKit or other session management system
        
        Returns:
            Current number of concurrent sessions
        """
        # For now, return a fixed value
        # In a real implementation, this would query active sessions
        return 1
    
    async def get_company_usage(
        self,
        session: AsyncSession,
        company_id: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime
    ) -> Dict[str, Any]:
        """
        Get aggregated usage metrics for a company in a date range
        
        Args:
            session: Database session
            company_id: Company identifier
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            Dictionary with aggregated usage metrics
        """
        # Get daily aggregates for the period
        stmt = select(DailyUsage).where(
            DailyUsage.company_id == company_id,
            DailyUsage.date >= start_date,
            DailyUsage.date < end_date
        ).order_by(DailyUsage.date)
        
        result = await session.execute(stmt)
        daily_records = result.scalars().all()
        
        # Calculate totals
        total_interactions = sum(record.total_interactions for record in daily_records)
        total_duration_ms = sum(record.total_duration_ms for record in daily_records)
        total_tokens = sum(record.total_tokens for record in daily_records)
        peak_concurrent = max((record.peak_concurrent_sessions for record in daily_records), default=0)
        
        # Get unique users across the whole period
        users_stmt = select(func.count(func.distinct(Usage.user_id))).where(
            Usage.company_id == company_id,
            Usage.timestamp >= start_date,
            Usage.timestamp < end_date,
            Usage.user_id != None
        )
        users_result = await session.execute(users_stmt)
        unique_users = users_result.scalar() or 0
        
        # Format as dictionary
        return {
            "company_id": company_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_interactions": total_interactions,
            "total_duration_ms": total_duration_ms,
            "total_minutes": round(total_duration_ms / 60000, 2),
            "total_tokens": total_tokens,
            "unique_users": unique_users,
            "peak_concurrent_sessions": peak_concurrent,
            "daily_breakdown": [
                {
                    "date": record.date.isoformat(),
                    "interactions": record.total_interactions,
                    "duration_ms": record.total_duration_ms,
                    "tokens": record.total_tokens
                }
                for record in daily_records
            ]
        }
    
    async def get_current_month_usage(
        self,
        session: AsyncSession,
        company_id: str
    ) -> Dict[str, Any]:
        """
        Get usage for the current month for quota checking
        
        Args:
            session: Database session
            company_id: Company identifier
            
        Returns:
            Dictionary with current month usage metrics
        """
        # Calculate start and end of current month
        today = datetime.datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return await self.get_company_usage(session, company_id, start_of_month, end_of_month)

# Create a singleton instance
usage_tracker = UsageTracker() 