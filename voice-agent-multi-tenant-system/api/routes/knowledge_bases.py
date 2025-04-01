"""
Knowledge Base API routes for managing knowledge bases and documents.
"""

import logging
import os
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import KnowledgeBase, KnowledgeBaseFile
from db.init_db import get_db
from services.knowledge_base.manager import KnowledgeBaseManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/knowledge-bases",
    tags=["knowledge_bases"],
)

@router.get("/", response_model=List[Dict])
async def list_knowledge_bases(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    List all knowledge bases for a company.
    
    Args:
        company_id: ID of the company
        
    Returns:
        List of knowledge base details
    """
    kb_manager = KnowledgeBaseManager(db)
    return await kb_manager.list_knowledge_bases(company_id)

@router.post("/", response_model=Dict)
async def create_knowledge_base(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new knowledge base for a company.
    
    Request Body:
        - company_id: ID of the company
        - name: Name of the knowledge base
        - description: Optional description
        
    Returns:
        The created knowledge base details
    """
    try:
        company_id = request.get("company_id")
        name = request.get("name")
        description = request.get("description")
        
        if not company_id or not name:
            raise HTTPException(status_code=400, detail="Company ID and name are required")
        
        kb_manager = KnowledgeBaseManager(db)
        knowledge_base = await kb_manager.create_knowledge_base(
            company_id=company_id,
            name=name,
            description=description
        )
        
        return {
            "id": knowledge_base.id,
            "company_id": knowledge_base.company_id,
            "name": knowledge_base.name,
            "description": knowledge_base.description,
            "file_count": knowledge_base.file_count,
            "total_size": knowledge_base.total_size,
            "status": knowledge_base.status,
            "created_at": knowledge_base.created_at.isoformat() if knowledge_base.created_at else None,
            "updated_at": knowledge_base.updated_at.isoformat() if knowledge_base.updated_at else None
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{knowledge_base_id}", response_model=Dict)
async def get_knowledge_base(
    knowledge_base_id: str,
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific knowledge base.
    
    Args:
        knowledge_base_id: ID of the knowledge base
        company_id: ID of the company
        
    Returns:
        Knowledge base details including files
    """
    try:
        kb_manager = KnowledgeBaseManager(db)
        knowledge_base = await kb_manager.get_knowledge_base(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id
        )
        
        if not knowledge_base:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        return knowledge_base
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{knowledge_base_id}", response_model=Dict)
async def delete_knowledge_base(
    knowledge_base_id: str,
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a knowledge base and all its documents.
    
    Args:
        knowledge_base_id: ID of the knowledge base
        company_id: ID of the company
        
    Returns:
        Success message
    """
    try:
        kb_manager = KnowledgeBaseManager(db)
        result = await kb_manager.delete_knowledge_base(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id
        )
        
        return {"success": result, "message": "Knowledge base deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{knowledge_base_id}/documents", response_model=Dict)
async def upload_document(
    knowledge_base_id: str,
    background_tasks: BackgroundTasks,
    company_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document to a knowledge base.
    
    Args:
        knowledge_base_id: ID of the knowledge base
        company_id: ID of the company
        file: The file to upload
        
    Returns:
        The created knowledge base file details
    """
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await file.read()
        
        # Get file type
        file_type = file.content_type
        
        kb_manager = KnowledgeBaseManager(db)
        kb_file, processing_started = await kb_manager.upload_document(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id,
            file_name=file.filename,
            file_content=file_content,
            file_type=file_type
        )
        
        # Start background processing
        if processing_started:
            background_tasks.add_task(
                kb_manager.process_document,
                company_id=company_id,
                file_id=kb_file.id
            )
        
        return {
            "id": kb_file.id,
            "knowledge_base_id": kb_file.knowledge_base_id,
            "name": kb_file.name,
            "file_type": kb_file.file_type,
            "size": kb_file.size,
            "status": kb_file.status,
            "file_path": kb_file.file_path,
            "created_at": kb_file.created_at.isoformat() if kb_file.created_at else None,
            "message": "File uploaded successfully. Processing started."
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{knowledge_base_id}/documents/{file_id}", response_model=Dict)
async def delete_document(
    knowledge_base_id: str,
    file_id: str,
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a document from a knowledge base.
    
    Args:
        knowledge_base_id: ID of the knowledge base
        file_id: ID of the file to delete
        company_id: ID of the company
        
    Returns:
        Success message
    """
    try:
        kb_manager = KnowledgeBaseManager(db)
        result = await kb_manager.delete_document(
            company_id=company_id,
            file_id=file_id
        )
        
        return {"success": result, "message": "Document deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/query", response_model=List[Dict])
async def query_knowledge_base(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Query knowledge bases for relevant information.
    
    Request Body:
        - company_id: ID of the company
        - query_text: The query text
        - knowledge_base_ids: Optional list of knowledge base IDs to search in
        - top_k: Number of results to return (default: 5)
        
    Returns:
        List of relevant document chunks with metadata
    """
    try:
        company_id = request.get("company_id")
        query_text = request.get("query_text")
        knowledge_base_ids = request.get("knowledge_base_ids")
        top_k = request.get("top_k", 5)
        
        if not company_id or not query_text:
            raise HTTPException(status_code=400, detail="Company ID and query text are required")
        
        kb_manager = KnowledgeBaseManager(db)
        results = await kb_manager.query_knowledge_base(
            company_id=company_id,
            query_text=query_text,
            knowledge_base_ids=knowledge_base_ids,
            top_k=top_k
        )
        
        return results
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 