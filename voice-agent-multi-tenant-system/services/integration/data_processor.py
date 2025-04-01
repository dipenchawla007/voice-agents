"""
Data Processor Service for company data integration.

This service handles processing and storing external data from companies,
which can then be accessed by voice agents during conversations.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import company_data, company_data_sync
from models.company import Company
from services.embedding.manager import EmbeddingManager

logger = logging.getLogger(__name__)

class DataProcessor:
    """Service for processing and storing company data for agent access."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the data processor with database session."""
        self.db = db
        self.embedding_manager = EmbeddingManager()
    
    async def process_company_data(
        self, 
        company_id: str, 
        data_type: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single data record for a company.
        
        Args:
            company_id: ID of the company
            data_type: Type of data (e.g., 'customers', 'products')
            data: The data record
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Validate company exists
            company = await self._get_company(company_id)
            if not company:
                raise ValueError(f"Company with ID {company_id} not found")
            
            # Generate a unique record ID if not provided
            record_id = data.get('id', str(hash(frozenset(data.items()))))
            
            # Check if record already exists
            existing = await self._get_company_data_record(company_id, data_type, record_id)
            
            # Prepare data for storage
            data_to_store = {
                "company_id": company_id,
                "data_type": data_type,
                "record_id": record_id,
                "data": json.dumps(data),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_deleted": False
            }
            
            # Generate embeddings for searchable content
            searchable_text = self._extract_searchable_text(data_type, data)
            if searchable_text:
                embedding = await self.embedding_manager.generate_embedding(searchable_text)
                data_to_store["embedding"] = embedding
            
            # Insert or update the record
            if existing:
                data_to_store.pop("created_at", None)  # Don't update created_at
                await self._update_company_data_record(company_id, data_type, record_id, data_to_store)
            else:
                await self._insert_company_data_record(data_to_store)
            
            # Update sync status
            await self._update_sync_status(company_id, data_type)
            
            return {
                "company_id": company_id,
                "data_type": data_type,
                "record_id": record_id,
                "records_processed": 1,
                "operation": "update" if existing else "insert"
            }
            
        except Exception as e:
            logger.error(f"Error processing company data: {str(e)}")
            raise
    
    async def process_batch_data(
        self, 
        company_id: str, 
        data_type: str, 
        batch_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a batch of data records for a company.
        
        Args:
            company_id: ID of the company
            data_type: Type of data (e.g., 'customers', 'products')
            batch_data: List of data records
            
        Returns:
            Dictionary with processing results
        """
        if not batch_data:
            return {"records_processed": 0}
        
        records_processed = 0
        
        try:
            # Validate company exists
            company = await self._get_company(company_id)
            if not company:
                raise ValueError(f"Company with ID {company_id} not found")
            
            # Process each record in the batch
            for data_record in batch_data:
                # Process the record and count successful operations
                result = await self.process_company_data(company_id, data_type, data_record)
                records_processed += result.get("records_processed", 0)
            
            # Update sync status for this data type
            await self._update_sync_status(company_id, data_type)
            
            return {
                "company_id": company_id,
                "data_type": data_type,
                "records_processed": records_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing batch data: {str(e)}")
            # Return partial success information
            return {
                "company_id": company_id,
                "data_type": data_type,
                "records_processed": records_processed,
                "error": str(e)
            }
    
    async def delete_company_data(
        self, 
        company_id: str, 
        data_type: str, 
        record_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Delete company data records.
        
        Args:
            company_id: ID of the company
            data_type: Type of data to delete
            record_ids: List of record IDs to delete
            
        Returns:
            Dictionary with deletion results
        """
        if not record_ids:
            return {"records_deleted": 0}
        
        try:
            # Soft delete the records (mark as deleted)
            query = (
                update(company_data)
                .where(
                    (company_data.c.company_id == company_id) &
                    (company_data.c.data_type == data_type) &
                    (company_data.c.record_id.in_(record_ids))
                )
                .values(is_deleted=True, updated_at=datetime.utcnow())
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            # Update sync status
            await self._update_sync_status(company_id, data_type)
            
            return {
                "company_id": company_id,
                "data_type": data_type,
                "records_deleted": result.rowcount
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting company data: {str(e)}")
            raise
    
    async def get_integration_status(self, company_id: str) -> Dict[str, Any]:
        """
        Get integration status for a company.
        
        Args:
            company_id: ID of the company
            
        Returns:
            Dictionary with integration status information
        """
        try:
            # Get all data types and their sync status
            query = (
                select([
                    company_data_sync.c.data_type,
                    company_data_sync.c.last_sync_time,
                    company_data_sync.c.record_count
                ])
                .where(company_data_sync.c.company_id == company_id)
            )
            
            result = await self.db.execute(query)
            sync_records = result.fetchall()
            
            # Get a list of connected sources
            connected_sources = set()
            data_types = []
            record_counts = {}
            last_sync = None
            
            for record in sync_records:
                data_type = record.data_type
                data_types.append(data_type)
                record_counts[data_type] = record.record_count
                
                # Extract source from data_type (e.g., 'zendesk:tickets' -> 'zendesk')
                if ':' in data_type:
                    source = data_type.split(':', 1)[0]
                    connected_sources.add(source)
                
                # Track most recent sync
                if last_sync is None or record.last_sync_time > last_sync:
                    last_sync = record.last_sync_time
            
            return {
                "connected_sources": list(connected_sources),
                "data_types": data_types,
                "record_counts": record_counts,
                "last_sync_timestamp": last_sync.isoformat() if last_sync else None
            }
            
        except Exception as e:
            logger.error(f"Error getting integration status: {str(e)}")
            return {
                "error": str(e),
                "connected_sources": [],
                "data_types": [],
                "record_counts": {}
            }
    
    async def search_company_data(
        self, 
        company_id: str, 
        query: str, 
        data_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search company data using semantic search.
        
        Args:
            company_id: ID of the company
            query: Search query
            data_types: Optional list of data types to search in
            limit: Maximum number of results to return
            
        Returns:
            List of matching data records
        """
        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_manager.generate_embedding(query)
            
            # Construct base query
            base_query = (
                select([
                    company_data.c.data_type,
                    company_data.c.record_id,
                    company_data.c.data,
                    # Calculate cosine similarity
                    self._cosine_similarity_expression(company_data.c.embedding, query_embedding).label("similarity")
                ])
                .where(
                    (company_data.c.company_id == company_id) &
                    (company_data.c.is_deleted == False) &
                    (company_data.c.embedding != None)
                )
                .order_by("similarity DESC")
                .limit(limit)
            )
            
            # Add data type filter if provided
            if data_types:
                base_query = base_query.where(company_data.c.data_type.in_(data_types))
            
            # Execute query
            result = await self.db.execute(base_query)
            records = result.fetchall()
            
            # Format results
            search_results = []
            for record in records:
                search_results.append({
                    "data_type": record.data_type,
                    "record_id": record.record_id,
                    "data": json.loads(record.data),
                    "similarity": float(record.similarity)
                })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching company data: {str(e)}")
            return []
    
    def _cosine_similarity_expression(self, embedding_col, query_embedding):
        """Generate SQL expression for cosine similarity calculation."""
        # The actual implementation depends on the database type
        # This is a simplified PostgreSQL example
        return f"embedding <=> '{query_embedding}'"
    
    def _extract_searchable_text(self, data_type: str, data: Dict[str, Any]) -> str:
        """
        Extract searchable text from data record based on data type.
        
        Different data types have different structures and important fields.
        """
        searchable_parts = []
        
        # Add type-specific extractors
        if data_type == "customers" or data_type.endswith(":customers"):
            for field in ["name", "email", "description", "notes"]:
                if field in data and data[field]:
                    searchable_parts.append(str(data[field]))
                    
        elif data_type == "products" or data_type.endswith(":products"):
            for field in ["name", "description", "category", "features"]:
                if field in data and data[field]:
                    searchable_parts.append(str(data[field]))
                    
        elif data_type == "tickets" or data_type.endswith(":tickets"):
            for field in ["subject", "description", "comments", "status"]:
                if field in data and data[field]:
                    if isinstance(data[field], list):
                        # Handle list fields like comments
                        for item in data[field]:
                            if isinstance(item, dict) and "body" in item:
                                searchable_parts.append(item["body"])
                            else:
                                searchable_parts.append(str(item))
                    else:
                        searchable_parts.append(str(data[field]))
                        
        # Generic fallback for unknown data types
        else:
            # Include common text fields
            for field in data:
                if isinstance(data[field], str) and len(data[field]) > 3:
                    searchable_parts.append(data[field])
                # Extract nested text fields if the value is a dictionary
                elif isinstance(data[field], dict):
                    for nested_field in ["name", "title", "description", "text", "body"]:
                        if nested_field in data[field]:
                            searchable_parts.append(str(data[field][nested_field]))
        
        return " ".join(searchable_parts)
    
    async def _get_company(self, company_id: str) -> Optional[Company]:
        """Get company by ID."""
        query = select(Company).where(Company.id == company_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_company_data_record(
        self, 
        company_id: str, 
        data_type: str, 
        record_id: str
    ) -> Optional[Dict]:
        """Get a company data record."""
        query = (
            select([company_data])
            .where(
                (company_data.c.company_id == company_id) &
                (company_data.c.data_type == data_type) &
                (company_data.c.record_id == record_id)
            )
        )
        result = await self.db.execute(query)
        return result.fetchone()
    
    async def _insert_company_data_record(self, data: Dict[str, Any]) -> None:
        """Insert a new company data record."""
        query = insert(company_data).values(**data)
        await self.db.execute(query)
        await self.db.commit()
    
    async def _update_company_data_record(
        self, 
        company_id: str, 
        data_type: str, 
        record_id: str, 
        data: Dict[str, Any]
    ) -> None:
        """Update an existing company data record."""
        query = (
            update(company_data)
            .where(
                (company_data.c.company_id == company_id) &
                (company_data.c.data_type == data_type) &
                (company_data.c.record_id == record_id)
            )
            .values(**data)
        )
        await self.db.execute(query)
        await self.db.commit()
    
    async def _update_sync_status(self, company_id: str, data_type: str) -> None:
        """Update the sync status for a data type."""
        # Count active records of this type
        count_query = (
            select([
                company_data.c.company_id,
                company_data.c.data_type,
                # Count non-deleted records
                sa.func.count().label("record_count")
            ])
            .where(
                (company_data.c.company_id == company_id) &
                (company_data.c.data_type == data_type) &
                (company_data.c.is_deleted == False)
            )
            .group_by(
                company_data.c.company_id,
                company_data.c.data_type
            )
        )
        count_result = await self.db.execute(count_query)
        count_record = count_result.fetchone()
        record_count = count_record.record_count if count_record else 0
        
        # Check if sync record exists
        sync_query = (
            select([company_data_sync])
            .where(
                (company_data_sync.c.company_id == company_id) &
                (company_data_sync.c.data_type == data_type)
            )
        )
        sync_result = await self.db.execute(sync_query)
        sync_record = sync_result.fetchone()
        
        # Create or update sync record
        now = datetime.utcnow()
        if sync_record:
            update_query = (
                update(company_data_sync)
                .where(
                    (company_data_sync.c.company_id == company_id) &
                    (company_data_sync.c.data_type == data_type)
                )
                .values(
                    last_sync_time=now,
                    record_count=record_count
                )
            )
            await self.db.execute(update_query)
        else:
            insert_query = insert(company_data_sync).values(
                company_id=company_id,
                data_type=data_type,
                last_sync_time=now,
                record_count=record_count
            )
            await self.db.execute(insert_query)
        
        await self.db.commit() 