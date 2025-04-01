"""
Document AI Service for text extraction from documents.

This service provides an interface to Google Document AI for extracting text
and structured content from various document types including PDFs, forms,
and images containing text.
"""

import logging
import os
from typing import Tuple, Dict, Any, Optional, List
from io import BytesIO

# For Document AI
from google.cloud import documentai

# For fallback processing
import PyPDF2

logger = logging.getLogger(__name__)

class DocumentAIService:
    """Service for extracting text from documents using Google Document AI"""

    def __init__(self):
        """
        Initialize Document AI service with configuration from environment variables
        """
        # Check if Document AI is enabled
        self.enabled = os.getenv("DOCUMENT_AI_ENABLED", "false").lower() == "true"
        
        if self.enabled:
            self.project_id = os.getenv("GCP_PROJECT_ID")
            self.location = os.getenv("DOCUMENT_AI_LOCATION", "us")
            self.processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
            self.processor_type = os.getenv("DOCUMENT_AI_PROCESSOR_TYPE", "GENERAL_DOCUMENT_PROCESSOR")
            
            if not all([self.project_id, self.processor_id]):
                logger.warning(
                    "Document AI enabled but missing configuration. "
                    "Ensure GCP_PROJECT_ID and DOCUMENT_AI_PROCESSOR_ID are set."
                )
                self.enabled = False
            else:
                logger.info(f"Document AI service initialized with processor {self.processor_id}")
        else:
            logger.info("Document AI service disabled, using fallback text extraction")

    async def process_document(
        self, 
        file_content: bytes, 
        mime_type: str
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process a document using Document AI or fallback methods if disabled
        
        Args:
            file_content: Raw bytes of the document
            mime_type: MIME type of the document
            
        Returns:
            Tuple of (extracted text, metadata dictionary)
            If Document AI is disabled, metadata will be None
        """
        if not self.enabled:
            logger.info("Using fallback document processing")
            return await self._fallback_process_document(file_content, mime_type), None
        
        try:
            # Initialize Document AI client
            client = documentai.DocumentProcessorServiceAsyncClient(
                client_options={"api_endpoint": f"{self.location}-documentai.googleapis.com"}
            )
            
            # Format the resource name
            resource_name = client.processor_path(
                project=self.project_id,
                location=self.location,
                processor=self.processor_id
            )
            
            # Create RawDocument
            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type=mime_type
            )
            
            # Configure the process request
            request = documentai.ProcessRequest(
                name=resource_name,
                raw_document=raw_document
            )
            
            # Process the document
            logger.info(f"Processing document with Document AI processor {self.processor_id}")
            operation = await client.process_document(request=request)
            document = operation.document
            
            # Extract text from the document
            full_text = document.text
            
            # Extract structured data from the document
            metadata = self._extract_document_metadata(document)
            
            # Log success and return results
            logger.info(f"Successfully processed document with Document AI. " +
                      f"Extracted {len(full_text)} characters of text.")
            return full_text, metadata
            
        except Exception as e:
            logger.error(f"Error processing document with Document AI: {str(e)}")
            logger.info("Falling back to basic text extraction")
            
            # Fall back to basic processing
            return await self._fallback_process_document(file_content, mime_type), None
    
    def _extract_document_metadata(self, document) -> Dict[str, Any]:
        """
        Extract metadata from a Document AI document
        
        Args:
            document: The Document AI document object
            
        Returns:
            Dictionary containing structured data extracted from the document
        """
        metadata = {}
        
        # Extract entities (like form fields)
        if document.entities:
            form_fields = {}
            for entity in document.entities:
                # Convert entity type to more readable format
                entity_type = entity.type_.lower().replace('_', ' ')
                
                # Get the entity text
                entity_text = self._get_text_from_layout(document, entity.page_anchor)
                
                # Skip empty entities
                if not entity_text.strip():
                    continue
                
                # Store as key-value pair
                form_fields[entity_type] = entity_text
            
            if form_fields:
                metadata["form_fields"] = form_fields
        
        # Extract tables
        if document.pages:
            tables = []
            for page in document.pages:
                if page.tables:
                    for table in page.tables:
                        table_data = []
                        
                        for row in table.body_rows:
                            row_data = []
                            for cell in row.cells:
                                cell_text = self._get_text_from_layout(document, cell.layout)
                                row_data.append(cell_text)
                            table_data.append(row_data)
                        
                        # Only add non-empty tables
                        if table_data:
                            tables.append(table_data)
            
            if tables:
                metadata["tables"] = tables
        
        return metadata
    
    def _get_text_from_layout(self, document, layout) -> str:
        """
        Extract text from a document layout element
        
        Args:
            document: The Document AI document object
            layout: A layout element with text reference
            
        Returns:
            The extracted text
        """
        if not layout or not document.text:
            return ""
        
        # Handle page anchor (multiple text segments)
        if hasattr(layout, 'page_refs') and layout.page_refs:
            text_parts = []
            for page_ref in layout.page_refs:
                if hasattr(page_ref, 'text_anchor') and page_ref.text_anchor:
                    for segment in page_ref.text_anchor.text_segments:
                        start_index = int(segment.start_index)
                        end_index = int(segment.end_index)
                        text_parts.append(document.text[start_index:end_index])
            return " ".join(text_parts)
        
        # Handle direct text anchor
        if hasattr(layout, 'text_anchor') and layout.text_anchor:
            text_parts = []
            for segment in layout.text_anchor.text_segments:
                start_index = int(segment.start_index)
                end_index = int(segment.end_index)
                text_parts.append(document.text[start_index:end_index])
            return " ".join(text_parts)
        
        return ""
    
    async def _fallback_process_document(self, file_content: bytes, mime_type: str) -> str:
        """
        Process a document using basic methods when Document AI is unavailable
        
        Args:
            file_content: Raw bytes of the document
            mime_type: MIME type of the document
            
        Returns:
            Extracted text from the document
        """
        try:
            # Process text files directly
            if mime_type.startswith('text/'):
                return file_content.decode('utf-8')
            
            # Process PDFs with PyPDF2
            elif mime_type == 'application/pdf':
                pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
            
            # Unsupported format
            else:
                logger.warning(f"Unsupported file type for fallback processing: {mime_type}")
                return ""
                
        except Exception as e:
            logger.error(f"Error in fallback document processing: {str(e)}")
            return "" 