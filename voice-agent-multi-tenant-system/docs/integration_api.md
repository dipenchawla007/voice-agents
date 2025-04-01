# Company Integration API Guide

This guide explains how to integrate your company's data with the Voice Agent Platform to provide agents with context from your business systems.

## Overview

The Integration API allows your systems to sync data with our platform, enabling voice agents to access relevant information when interacting with your customers. This creates more personalized and effective voice interactions.

## Authentication

All API requests require authentication using your company API key. Include this key in the request header:

```
X-API-Key: your_company_api_key_here
```

You can obtain or manage your API keys from the admin dashboard or by contacting support.

## Base URL

```
https://api.voiceagent.example.com/api/v1/integration
```

## Standard Data Endpoints

### Sync a Single Record

**POST** `/data/sync`

Sync a single data record to the platform.

**Query Parameters:**
- `data_type` (required): Type of data being synced (e.g., "customers", "products", "tickets")

**Request Body:**
```json
{
  "id": "record123",
  "name": "Example Record",
  "description": "This is an example record",
  // Additional fields specific to your data type
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed customers data",
  "records_processed": 1,
  "timestamp": "2023-07-01T14:30:00.000Z"
}
```

### Batch Sync Multiple Records

**POST** `/data/batch`

Sync multiple records at once for better performance.

**Query Parameters:**
- `data_type` (required): Type of data being synced

**Request Body:**
```json
[
  {
    "id": "record123",
    "name": "Example Record 1",
    // Additional fields
  },
  {
    "id": "record124",
    "name": "Example Record 2",
    // Additional fields
  }
]
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed batch customers data",
  "batch_size": 2,
  "records_processed": 2,
  "timestamp": "2023-07-01T14:30:00.000Z"
}
```

### Delete Records

**DELETE** `/data/{data_type}`

Mark records as deleted so they're no longer accessible to agents.

**Path Parameters:**
- `data_type`: Type of data to delete

**Request Body:**
```json
{
  "record_ids": ["record123", "record124"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully deleted customers data",
  "records_deleted": 2,
  "timestamp": "2023-07-01T14:30:00.000Z"
}
```

### Check Integration Status

**GET** `/status`

Check the status of your data integrations.

**Response:**
```json
{
  "company_id": "comp_123456",
  "connected_sources": ["zendesk", "notion"],
  "last_sync_timestamp": "2023-07-01T14:30:00.000Z",
  "data_types": ["zendesk:tickets", "zendesk:users", "notion:pages"],
  "record_counts": {
    "zendesk:tickets": 152,
    "zendesk:users": 45,
    "notion:pages": 23
  },
  "status": "active"
}
```

## Zendesk Integration Endpoints

### Sync Zendesk Tickets

**POST** `/zendesk/tickets`

Sync Zendesk tickets with the platform.

**Request Body:**
```json
[
  {
    "id": 12345,
    "subject": "Need help with integration",
    "description": "I'm having trouble setting up the API integration",
    "status": "open",
    "priority": "normal",
    "requester_id": 67890,
    "assignee_id": 54321,
    "comments": [
      {
        "id": 98765,
        "author_id": 67890,
        "body": "Here's some additional information..."
      }
    ],
    "created_at": "2023-06-28T10:15:00Z",
    "updated_at": "2023-06-29T14:30:00Z"
  }
]
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed Zendesk tickets",
  "tickets_processed": 1,
  "timestamp": "2023-07-01T14:30:00.000Z"
}
```

### Sync Zendesk Users

**POST** `/zendesk/users`

Sync Zendesk users with the platform.

**Request Body:**
```json
[
  {
    "id": 67890,
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "phone": "+1-555-123-4567",
    "created_at": "2023-01-15T12:00:00Z",
    "user_fields": {
      "account_type": "premium",
      "region": "west"
    }
  }
]
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed Zendesk users",
  "users_processed": 1,
  "timestamp": "2023-07-01T14:30:00.000Z"
}
```

## Notion Integration Endpoints

### Sync Notion Pages

**POST** `/notion/pages`

Sync Notion pages with the platform.

**Query Parameters:**
- `database_id` (optional): Notion database ID for context

**Request Body:**
```json
[
  {
    "id": "page_id_123",
    "url": "https://notion.so/mypage",
    "properties": {
      "title": {
        "type": "title",
        "title": [
          {
            "plain_text": "Product Documentation"
          }
        ]
      },
      "Status": {
        "type": "select",
        "select": {
          "name": "Published"
        }
      }
    },
    "content": [
      {
        "type": "paragraph",
        "paragraph": {
          "rich_text": [
            {
              "plain_text": "This is the product documentation."
            }
          ]
        }
      }
    ],
    "created_time": "2023-06-28T10:15:00Z",
    "last_edited_time": "2023-06-29T14:30:00Z"
  }
]
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed Notion pages",
  "pages_processed": 1,
  "timestamp": "2023-07-01T14:30:00.000Z"
}
```

### Sync Notion Database

**POST** `/notion/databases`

Sync a Notion database structure and optionally its pages.

**Query Parameters:**
- `include_pages` (optional, default: false): Whether to include database pages

**Request Body:**
```json
{
  "id": "database_id_123",
  "title": [
    {
      "plain_text": "Product Database"
    }
  ],
  "properties": {
    "Name": {
      "id": "title",
      "type": "title"
    },
    "Status": {
      "id": "status",
      "type": "select",
      "select": {
        "options": [
          { "name": "Draft" },
          { "name": "Published" }
        ]
      }
    }
  },
  "pages": [
    // Optional array of pages if include_pages=true
  ],
  "created_time": "2023-06-28T10:15:00Z",
  "last_edited_time": "2023-06-29T14:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully processed Notion database",
  "database_id": "database_id_123",
  "pages_processed": 0,
  "timestamp": "2023-07-01T14:30:00.000Z"
}
```

## Data Type Guidelines

When syncing data, use consistent data types to organize your information. Here are recommended data types:

- `customers`: Customer/user profiles
- `products`: Product information
- `tickets`: Support tickets or cases
- `orders`: Order information
- `invoices`: Invoice data
- `knowledge`: Knowledge base articles
- `faqs`: Frequently asked questions

You can also use namespaced data types for specific integrations:
- `zendesk:tickets`
- `zendesk:users`
- `notion:pages`
- `notion:databases`

## Best Practices

1. **Regular Updates**: Set up regular syncs to keep data current
2. **Selective Syncing**: Only sync the fields that agents need
3. **Batch Processing**: Use batch endpoints for large data sets
4. **Error Handling**: Monitor responses for errors and retry failed requests
5. **Permissions**: Only sync data that is appropriate for customer interactions
6. **Private Data**: Never include sensitive personal data or security information

## Embedding and Search

The platform automatically generates embeddings for your data, enabling semantic search capabilities. Focus on including descriptive text fields to improve search relevance.

## Rate Limits

The API is subject to the following rate limits:
- 100 requests per minute
- 10,000 records per day

If you need higher limits, please contact support.

## Support

For additional help or to report issues, contact our integration team at:
- Email: integrations@voiceagent.example.com
- Support Portal: https://support.voiceagent.example.com 