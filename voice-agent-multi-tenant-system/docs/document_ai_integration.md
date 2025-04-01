# Document AI Integration Guide

This guide explains how to set up and use the Google Document AI integration for enhanced document processing within the voice agent multi-tenant system.

## Overview

The Document AI integration allows for advanced document processing capabilities:

- Improved text extraction from PDFs, forms, and images with text
- Structured data extraction (tables, form fields)
- Better handling of complex document layouts
- Multi-language support
- OCR capabilities for image-based documents

## Prerequisites

1. A Google Cloud Platform account with billing enabled
2. Permissions to create and manage Document AI processors
3. Access to the Document AI API

## Setting Up Document AI

### 1. Enable the Document AI API

```bash
# Enable the Document AI API in your project
gcloud services enable documentai.googleapis.com --project=YOUR_PROJECT_ID
```

### 2. Create a Document AI Processor

1. Go to the [Document AI Console](https://console.cloud.google.com/ai/document-ai)
2. Click "Create Processor"
3. Select the processor type based on your needs:
   - **General Document OCR**: For basic text extraction from various documents
   - **Form Parser**: For extracting form fields and structured data
   - **Document Splitter**: For processing multi-page documents
   - **Custom Document Extractor**: For creating your own custom extractors

4. Choose a location for your processor (e.g., "us", "eu")
5. Name your processor and create it

### 3. Get Processor Details

After creating the processor, note the following details:
- Processor ID
- Processor type
- Location

## Configuration in Voice Agent System

### 1. Update Environment Variables

Add the following variables to your `.env` file:

```
# Document AI Configuration
DOCUMENT_AI_ENABLED=true
GCP_PROJECT_ID=your-project-id
DOCUMENT_AI_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=your-processor-id
DOCUMENT_AI_PROCESSOR_TYPE=GENERAL_DOCUMENT_PROCESSOR
```

Valid processor types include:
- `GENERAL_DOCUMENT_PROCESSOR`
- `FORM_PARSER_PROCESSOR`
- `DOCUMENT_SPLITTER_PROCESSOR`
- `CUSTOM_EXTRACTOR_PROCESSOR`

### 2. Service Account Setup

Ensure your application has the necessary permissions to access Document AI:

1. Create a service account or use an existing one:
```bash
gcloud iam service-accounts create document-ai-user --display-name="Document AI User"
```

2. Grant the service account access to Document AI:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:document-ai-user@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/documentai.user"
```

3. Create and download a key for the service account:
```bash
gcloud iam service-accounts keys create document-ai-key.json \
    --iam-account=document-ai-user@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

4. Set the environment variable to point to the key file:
```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/document-ai-key.json
```

## Using Document AI in the Application

The system now automatically uses Document AI for document processing when uploading documents to knowledge bases.

### Key Components

- **DocumentAIService**: Handles communication with Document AI API
- **KnowledgeBaseManager**: Uses DocumentAIService for processing documents
- **SmartChunkingService**: Intelligently chunks document content based on structure

### Document Processing Flow

1. Document is uploaded to a knowledge base
2. File is stored in Google Cloud Storage
3. DocumentAIService processes the document using Document AI
4. Text and structured data are extracted
5. SmartChunkingService chunks the content intelligently
6. Chunks are embedded and stored in Pinecone
7. Document is ready for retrieval in agent conversations

## Fallback Processing

If Document AI is disabled or encounters an error, the system automatically falls back to basic processing:
- Text files are processed directly
- PDFs are processed using PyPDF2
- Other file types may not be supported in fallback mode

## Monitoring and Troubleshooting

### Monitoring Document AI Usage

Monitor your Document AI usage in the Google Cloud Console:
- Go to the [Document AI Console](https://console.cloud.google.com/ai/document-ai)
- Click on your processor
- View the "Metrics" tab

### Common Issues and Solutions

1. **Document AI not processing documents**:
   - Check that `DOCUMENT_AI_ENABLED` is set to `true`
   - Verify processor ID and other configuration variables
   - Ensure service account has the correct permissions

2. **Poor quality text extraction**:
   - Consider using a different processor type
   - Check document quality and format
   
3. **Rate limiting or quota issues**:
   - Monitor usage in Google Cloud Console
   - Request quota increases if needed
   - Implement request batching or queuing for high-volume processing

## Performance Considerations

- Document AI processing is billed per page processed
- Large documents may take longer to process
- Consider implementing asynchronous processing for large documents
- Use batch processing for multiple documents when possible

## Security Considerations

- Document AI temporary stores your documents during processing
- Data is encrypted in transit and at rest
- Configure data retention policies as needed
- Review Google Cloud security documentation for additional guidance 