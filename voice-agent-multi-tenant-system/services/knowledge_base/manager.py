"""
Knowledge Base Manager Service.

This service manages the creation, storage, processing, and retrieval of 
documents for agent knowledge bases. It handles:
1. Document upload and storage in Google Cloud Storage
2. Text extraction using Document AI
3. Smart text chunking and embedding generation
4. Storage of embeddings in Pinecone
5. Retrieval of relevant document chunks for queries
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from io import BytesIO

from google.cloud import storage
import pinecone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from db.schemas import KnowledgeBase, KnowledgeBaseFile
from services.quota.manager import QuotaManager
from services.knowledge_base.document_ai import DocumentAIService

logger = logging.getLogger(__name__)

class SmartChunkingService:
    """
    Enhanced chunking service that intelligently splits text based on 
    semantic boundaries and document structure.
    """
    
    def __init__(self, 
                 max_chunk_size: int = 500, 
                 chunk_overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Split text into smart chunks based on document structure
        
        Args:
            text: The text to chunk
            metadata: Optional document metadata from Document AI
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        # If Document AI provided tables, we can process them separately
        if metadata and "tables" in metadata:
            # Extract and process tables as separate chunks
            # This is valuable for structured data
            for table in metadata["tables"]:
                table_text = self._process_table(table)
                if table_text:
                    chunks.append(table_text)
        
        # If Document AI provided form fields, process them as key-value pairs
        if metadata and "form_fields" in metadata:
            form_text = self._process_form_fields(metadata["form_fields"])
            if form_text:
                chunks.append(form_text)
        
        # Process the main text body, excluding already processed parts
        # This is a simplified chunking approach that splits by paragraphs and sentences
        # First split by paragraphs
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            # If paragraph is very large, split it further
            if len(paragraph) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    # Keep some overlap
                    if len(current_chunk) > 1:
                        current_chunk = current_chunk[-1:]
                        current_size = len(current_chunk[0])
                    else:
                        current_chunk = []
                        current_size = 0
                
                # Split large paragraph into sentences
                sentences = [s.strip() + "." for s in paragraph.split(".") if s.strip()]
                sentence_chunks = []
                current_sentence_chunk = []
                current_sentence_size = 0
                
                for sentence in sentences:
                    if current_sentence_size + len(sentence) <= self.max_chunk_size:
                        current_sentence_chunk.append(sentence)
                        current_sentence_size += len(sentence)
                    else:
                        if current_sentence_chunk:
                            sentence_chunks.append(" ".join(current_sentence_chunk))
                        current_sentence_chunk = [sentence]
                        current_sentence_size = len(sentence)
                
                if current_sentence_chunk:
                    sentence_chunks.append(" ".join(current_sentence_chunk))
                
                chunks.extend(sentence_chunks)
            
            # Normal paragraph handling
            elif current_size + len(paragraph) <= self.max_chunk_size:
                current_chunk.append(paragraph)
                current_size += len(paragraph)
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    # Keep some overlap for context
                    if len(current_chunk) > 1 and len(current_chunk[-1]) < self.chunk_overlap:
                        current_chunk = current_chunk[-1:]
                        current_size = len(current_chunk[0])
                    else:
                        current_chunk = []
                        current_size = 0
                current_chunk.append(paragraph)
                current_size = len(paragraph)
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _process_table(self, table: List[List[str]]) -> str:
        """
        Process a table into a textual representation
        
        Args:
            table: A table represented as a list of rows, each containing cells
            
        Returns:
            Textual representation of the table
        """
        table_text = "Table contents:\n"
        
        # Process header row if it exists
        if table and len(table) > 0:
            # Assume first row might be header
            headers = table[0]
            
            # Process other rows
            for i, row in enumerate(table[1:], 1):
                row_text = ""
                for j, cell in enumerate(row):
                    if j < len(headers):
                        row_text += f"{headers[j]}: {cell}; "
                    else:
                        row_text += f"Column {j}: {cell}; "
                table_text += row_text.strip() + "\n"
        
        return table_text
    
    def _process_form_fields(self, form_fields: Dict[str, str]) -> str:
        """
        Process form fields into a textual representation
        
        Args:
            form_fields: Dictionary of form field names and values
            
        Returns:
            Textual representation of form fields
        """
        form_text = "Form contents:\n"
        
        for field_name, field_value in form_fields.items():
            form_text += f"{field_name}: {field_value}\n"
        
        return form_text


class KnowledgeBaseManager:
    """Service for managing knowledge bases and document storage/retrieval"""
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the knowledge base manager
        
        Args:
            db_session: SQLAlchemy async session for database operations
        """
        self.db_session = db_session
        self.storage_client = self._init_storage_client()
        self.pinecone_index = self._init_pinecone()
        self.chunking_service = SmartChunkingService()
        self.document_ai = DocumentAIService()
        self.quota_manager = QuotaManager(db_session)
        
        # GCS bucket for document storage
        self.bucket_name = os.getenv("GCP_STORAGE_BUCKET", "voice-agent-knowledge-base")
        
        # OpenAI embedding model - could be configurable
        self.embedding_model = "text-embedding-3-small"
    
    def _init_storage_client(self):
        """Initialize Google Cloud Storage client"""
        # Check if credentials file is specified
        credentials_file = os.getenv("GCP_CREDENTIALS_FILE")
        if credentials_file:
            return storage.Client.from_service_account_json(credentials_file)
        else:
            # Use default credentials (GOOGLE_APPLICATION_CREDENTIALS env var)
            return storage.Client()
    
    def _init_pinecone(self):
        """Initialize Pinecone client and index"""
        pinecone.init(
            api_key=os.getenv("PINECONE_API_KEY"),
            environment=os.getenv("PINECONE_ENVIRONMENT")
        )
        
        index_name = os.getenv("PINECONE_INDEX", "voice-agent-kb")
        
        # Check if index exists, create if it doesn't
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine"
            )
            logger.info(f"Created new Pinecone index: {index_name}")
        
        return pinecone.Index(index_name)
    
    async def create_knowledge_base(self, 
                                   company_id: str, 
                                   name: str, 
                                   description: Optional[str] = None) -> KnowledgeBase:
        """
        Create a new knowledge base for a company
        
        Args:
            company_id: ID of the company
            name: Name of the knowledge base
            description: Optional description
            
        Returns:
            The created knowledge base object
        """
        # Check knowledge base quota
        quota_check = await self.quota_manager.check_knowledge_base_quota(
            company_id=company_id, 
            file_size_mb=0  # Just checking if another KB can be created
        )
        
        if not quota_check["allowed"]:
            raise ValueError(f"Knowledge base quota exceeded: {quota_check['message']}")
        
        # Create knowledge base record
        kb_id = str(uuid.uuid4())
        knowledge_base = KnowledgeBase(
            id=kb_id,
            company_id=company_id,
            name=name,
            description=description,
            file_count=0,
            total_size=0,
            status="active"
        )
        
        self.db_session.add(knowledge_base)
        await self.db_session.commit()
        await self.db_session.refresh(knowledge_base)
        
        logger.info(f"Created knowledge base {kb_id} for company {company_id}")
        return knowledge_base
    
    async def upload_document(self, 
                             company_id: str, 
                             knowledge_base_id: str, 
                             file_name: str,
                             file_content: bytes,
                             file_type: str) -> Tuple[KnowledgeBaseFile, bool]:
        """
        Upload a document to a knowledge base
        
        Args:
            company_id: ID of the company
            knowledge_base_id: ID of the knowledge base
            file_name: Name of the file
            file_content: Binary content of the file
            file_type: MIME type of the file
            
        Returns:
            The created knowledge base file object and a boolean indicating
            whether processing was started
        """
        # Verify knowledge base exists and belongs to company
        kb_query = select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.company_id == company_id
        )
        result = await self.db_session.execute(kb_query)
        knowledge_base = result.scalars().first()
        
        if not knowledge_base:
            raise ValueError(f"Knowledge base {knowledge_base_id} not found for company {company_id}")
        
        # Check file size quota
        file_size_mb = len(file_content) / (1024 * 1024)
        quota_check = await self.quota_manager.check_knowledge_base_quota(
            company_id=company_id, 
            file_size_mb=file_size_mb
        )
        
        if not quota_check["allowed"]:
            raise ValueError(f"Knowledge base size quota exceeded: {quota_check['message']}")
        
        # Create a unique file ID and GCS path
        file_id = str(uuid.uuid4())
        file_path = f"companies/{company_id}/knowledge_base/{knowledge_base_id}/{file_id}/{file_name}"
        
        # Create knowledge base file record
        kb_file = KnowledgeBaseFile(
            id=file_id,
            knowledge_base_id=knowledge_base_id,
            name=file_name,
            file_type=file_type,
            size=len(file_content),
            status="processing",
            file_path=file_path
        )
        
        # Upload to GCS
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(file_path)
            blob.upload_from_string(file_content, content_type=file_type)
            
            # Update knowledge base stats
            knowledge_base.file_count += 1
            knowledge_base.total_size += len(file_content)
            
            # Save to database
            self.db_session.add(kb_file)
            await self.db_session.commit()
            await self.db_session.refresh(kb_file)
            
            # Start processing asynchronously
            # In a real implementation, this would be a background task
            # Here we'll just return that processing has started
            
            logger.info(f"Uploaded document {file_id} to knowledge base {knowledge_base_id}")
            return kb_file, True
            
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            kb_file.status = "error"
            await self.db_session.commit()
            raise
    
    async def process_document(self, company_id: str, file_id: str):
        """
        Process a document by extracting text, chunking, and creating embeddings
        
        Args:
            company_id: ID of the company
            file_id: ID of the file to process
        """
        # Get file info
        file_query = select(KnowledgeBaseFile).join(
            KnowledgeBase, 
            KnowledgeBaseFile.knowledge_base_id == KnowledgeBase.id
        ).where(
            KnowledgeBaseFile.id == file_id,
            KnowledgeBase.company_id == company_id
        )
        
        result = await self.db_session.execute(file_query)
        kb_file = result.scalars().first()
        
        if not kb_file:
            raise ValueError(f"File {file_id} not found for company {company_id}")
        
        try:
            # Download from GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(kb_file.file_path)
            file_content = blob.download_as_bytes()
            
            # Process with Document AI
            text, metadata = await self.document_ai.process_document(
                file_content=file_content,
                mime_type=kb_file.file_type
            )
            
            if not text:
                raise ValueError(f"No text extracted from document: {kb_file.name}")
            
            # Store document metadata in the database
            # This could be implemented by adding a metadata JSON field to KnowledgeBaseFile model
            
            # Chunk the text using our smart chunking service
            chunks = self.chunking_service.chunk_text(text, metadata)
            
            # Generate embeddings using OpenAI
            import openai
            
            # Configure OpenAI API
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
            # Process chunks in batches to avoid rate limits
            batch_size = 10
            vectors_to_upsert = []
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i+batch_size]
                
                # Generate embeddings for the batch
                response = await openai.embeddings.acreate(
                    model=self.embedding_model,
                    input=batch_chunks
                )
                
                # Process each embedding
                for j, embedding_data in enumerate(response.data):
                    chunk_index = i + j
                    vector = embedding_data.embedding
                    chunk_text = chunks[chunk_index]
                    
                    # Create unique ID for this chunk
                    chunk_id = f"{company_id}_{kb_file.knowledge_base_id}_{file_id}_{chunk_index}"
                    
                    # Prepare vector for Pinecone
                    vectors_to_upsert.append(
                        (
                            chunk_id, 
                            vector,
                            {
                                "company_id": company_id,
                                "knowledge_base_id": kb_file.knowledge_base_id,
                                "file_id": file_id,
                                "chunk_index": chunk_index,
                                "text": chunk_text[:1000],  # Truncate for metadata size limits
                                "file_name": kb_file.name
                            }
                        )
                    )
            
            # Upsert vectors to Pinecone in batches
            batch_size = 100  # Pinecone batch size limit
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i+batch_size]
                self.pinecone_index.upsert(vectors=batch)
            
            # Update file status
            kb_file.status = "active"
            await self.db_session.commit()
            
            logger.info(f"Processed document {file_id} with {len(chunks)} chunks using Document AI")
            
        except Exception as e:
            logger.error(f"Error processing document {file_id}: {str(e)}")
            kb_file.status = "error"
            await self.db_session.commit()
            raise
    
    async def query_knowledge_base(self, 
                                  company_id: str, 
                                  query_text: str,
                                  knowledge_base_ids: Optional[List[str]] = None,
                                  top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query knowledge bases for relevant information
        
        Args:
            company_id: ID of the company
            query_text: The query text
            knowledge_base_ids: Optional list of knowledge base IDs to search in
            top_k: Number of results to return
            
        Returns:
            List of relevant document chunks with metadata
        """
        # Generate embedding for query using OpenAI
        import openai
        
        # Configure OpenAI API
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Generate embedding for the query
        response = await openai.embeddings.acreate(
            model=self.embedding_model,
            input=query_text
        )
        
        # Get the embedding vector
        query_vector = response.data[0].embedding
        
        # Build filter based on company and optional knowledge base IDs
        filter_dict = {"company_id": {"$eq": company_id}}
        
        if knowledge_base_ids:
            filter_dict["knowledge_base_id"] = {"$in": knowledge_base_ids}
        
        # Query Pinecone
        results = self.pinecone_index.query(
            vector=query_vector,
            filter=filter_dict,
            top_k=top_k,
            include_metadata=True
        )
        
        # Format results
        formatted_results = []
        for match in results["matches"]:
            formatted_results.append({
                "text": match["metadata"]["text"],
                "file_name": match["metadata"]["file_name"],
                "file_id": match["metadata"]["file_id"],
                "knowledge_base_id": match["metadata"]["knowledge_base_id"],
                "score": match["score"]
            })
        
        return formatted_results
    
    async def delete_document(self, company_id: str, file_id: str) -> bool:
        """
        Delete a document and its embeddings
        
        Args:
            company_id: ID of the company
            file_id: ID of the file to delete
            
        Returns:
            True if deleted successfully
        """
        # Get file info
        file_query = select(KnowledgeBaseFile).join(
            KnowledgeBase, 
            KnowledgeBaseFile.knowledge_base_id == KnowledgeBase.id
        ).where(
            KnowledgeBaseFile.id == file_id,
            KnowledgeBase.company_id == company_id
        )
        
        result = await self.db_session.execute(file_query)
        kb_file = result.scalars().first()
        
        if not kb_file:
            raise ValueError(f"File {file_id} not found for company {company_id}")
        
        knowledge_base_id = kb_file.knowledge_base_id
        file_size = kb_file.size
        
        try:
            # Delete from GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(kb_file.file_path)
            blob.delete()
            
            # Delete vectors from Pinecone
            # Delete vectors with matching prefix
            self.pinecone_index.delete(
                filter={
                    "company_id": {"$eq": company_id},
                    "file_id": {"$eq": file_id}
                }
            )
            
            # Update knowledge base stats
            kb_query = select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.company_id == company_id
            )
            result = await self.db_session.execute(kb_query)
            knowledge_base = result.scalars().first()
            
            if knowledge_base:
                knowledge_base.file_count = max(0, knowledge_base.file_count - 1)
                knowledge_base.total_size = max(0, knowledge_base.total_size - file_size)
            
            # Delete file record
            await self.db_session.delete(kb_file)
            await self.db_session.commit()
            
            logger.info(f"Deleted document {file_id} from knowledge base {knowledge_base_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {file_id}: {str(e)}")
            await self.db_session.rollback()
            raise
    
    async def delete_knowledge_base(self, company_id: str, knowledge_base_id: str) -> bool:
        """
        Delete a knowledge base and all its documents
        
        Args:
            company_id: ID of the company
            knowledge_base_id: ID of the knowledge base to delete
            
        Returns:
            True if deleted successfully
        """
        # Verify knowledge base exists and belongs to company
        kb_query = select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.company_id == company_id
        )
        result = await self.db_session.execute(kb_query)
        knowledge_base = result.scalars().first()
        
        if not knowledge_base:
            raise ValueError(f"Knowledge base {knowledge_base_id} not found for company {company_id}")
        
        # Get all files for this knowledge base
        files_query = select(KnowledgeBaseFile).where(
            KnowledgeBaseFile.knowledge_base_id == knowledge_base_id
        )
        result = await self.db_session.execute(files_query)
        kb_files = result.scalars().all()
        
        try:
            # Delete all files from GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            for kb_file in kb_files:
                blob = bucket.blob(kb_file.file_path)
                blob.delete()
            
            # Delete all vectors from Pinecone
            self.pinecone_index.delete(
                filter={
                    "company_id": {"$eq": company_id},
                    "knowledge_base_id": {"$eq": knowledge_base_id}
                }
            )
            
            # Delete knowledge base and all files (cascade delete will handle files)
            await self.db_session.delete(knowledge_base)
            await self.db_session.commit()
            
            logger.info(f"Deleted knowledge base {knowledge_base_id} with {len(kb_files)} files")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting knowledge base {knowledge_base_id}: {str(e)}")
            await self.db_session.rollback()
            raise
    
    async def get_knowledge_base(self, company_id: str, knowledge_base_id: str) -> Optional[Dict]:
        """
        Get knowledge base details
        
        Args:
            company_id: ID of the company
            knowledge_base_id: ID of the knowledge base
            
        Returns:
            Knowledge base details or None if not found
        """
        kb_query = select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.company_id == company_id
        )
        result = await self.db_session.execute(kb_query)
        knowledge_base = result.scalars().first()
        
        if not knowledge_base:
            return None
        
        # Get all files for this knowledge base
        files_query = select(KnowledgeBaseFile).where(
            KnowledgeBaseFile.knowledge_base_id == knowledge_base_id
        )
        result = await self.db_session.execute(files_query)
        kb_files = result.scalars().all()
        
        files = []
        for kb_file in kb_files:
            files.append({
                "id": kb_file.id,
                "name": kb_file.name,
                "file_type": kb_file.file_type,
                "size": kb_file.size,
                "status": kb_file.status,
                "created_at": kb_file.created_at.isoformat() if kb_file.created_at else None
            })
        
        return {
            "id": knowledge_base.id,
            "name": knowledge_base.name,
            "description": knowledge_base.description,
            "file_count": knowledge_base.file_count,
            "total_size": knowledge_base.total_size,
            "status": knowledge_base.status,
            "created_at": knowledge_base.created_at.isoformat() if knowledge_base.created_at else None,
            "updated_at": knowledge_base.updated_at.isoformat() if knowledge_base.updated_at else None,
            "files": files
        }
    
    async def list_knowledge_bases(self, company_id: str) -> List[Dict]:
        """
        List all knowledge bases for a company
        
        Args:
            company_id: ID of the company
            
        Returns:
            List of knowledge base details
        """
        kb_query = select(KnowledgeBase).where(
            KnowledgeBase.company_id == company_id
        )
        result = await self.db_session.execute(kb_query)
        knowledge_bases = result.scalars().all()
        
        kb_list = []
        for kb in knowledge_bases:
            kb_list.append({
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "file_count": kb.file_count,
                "total_size": kb.total_size,
                "status": kb.status,
                "created_at": kb.created_at.isoformat() if kb.created_at else None,
                "updated_at": kb.updated_at.isoformat() if kb.updated_at else None
            })
        
        return kb_list 