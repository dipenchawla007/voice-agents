# Voice Agent Multi-Tenant System

A framework for building a multi-company voice agent platform with LiveKit integration.

## Overview

This system provides a multi-tenant architecture for conversational AI agents with real-time voice capabilities. It enables:

- Strong isolation between companies
- Detailed usage tracking for billing
- Quota enforcement at various levels
- Granular permissions management
- Access control and revocation
- Comprehensive billing based on actual usage

## Architecture

The system is designed with a layered architecture:

```
+---------------------+            +----------------------+            +------------------+
| Company Websites    |            | Voice Agent Platform |            | LiveKit Services |
|                     |            |                      |            |                  |
| +-----------------+ |            | +------------------+ |            | +--------------+ |
| | Embedded Widget | |<---------->| | Company Gateway  | |<---------->| | Voice/Video  | |
| +-----------------+ |            | +------------------+ |            | | Streaming    | |
|                     |            |         |            |            | +--------------+ |
+---------------------+            |         v            |            |        |         |
                                   | +------------------+ |            |        v         |
                                   | | Company Manager  | |            | +--------------+ |
                                   | +------------------+ |            | | Room Mgmt    | |
                                   |         |            |            | +--------------+ |
                                   |         v            |            +------------------+
                                   | +------------------+ |                     ^
                                   | | Token Generator  | |                     |
                                   | +------------------+ |                     |
                                   |         |            |            +------------------+
                                   |         v            |            | AI Service APIs  |
                                   | +------------------+ |            |                  |
                                   | | Agent Manager    | |<---------->| * STT Services   |
                                   | +------------------+ |            | * TTS Services   |
                                   |         |            |            | * LLM Providers  |
                                   |         v            |            | * Knowledge DBs  |
                                   | +------------------+ |            +------------------+
                                   | | Usage Tracker    | |
                                   | +------------------+ |
                                   |         |            |
                                   |         v            |
                                   | +------------------+ |
                                   | | Billing System   | |
                                   | +------------------+ |
                                   +----------------------+
```

## Features

- **Company Isolation**: Room prefixing and token-based separation
- **API Key Management**: Central management with BYOK option
- **Usage Tracking**: Detailed session, token, and time tracking
- **Quota Enforcement**: Limits on usage, agents, and resources
- **Billing**: Usage-based billing with tiered pricing
- **Dashboard**: Company-specific dashboard and admin views
- **Widget Integration**: Embed code for website integration

## Key Components

- **Token Service**: Generates LiveKit tokens with company isolation
- **Company Key Manager**: Securely stores and manages API keys
- **Usage Tracker**: Logs and aggregates usage metrics
- **Quota Manager**: Enforces limits and quotas
- **Agent Manager**: Creates and manages voice agents
- **Knowledge Base Manager**: Processes and embeds documents

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- LiveKit account and server
- API keys for AI services (optional)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env with your configuration
   ```
4. Initialize the database:
   ```
   alembic upgrade head
   ```
5. Start the server:
   ```
   uvicorn main:app --reload
   ```

## Configuration

The system uses environment variables for configuration:

- `DATABASE_URL`: PostgreSQL connection string
- `LIVEKIT_URL`: LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `JWT_SECRET`: Secret for JWT token generation
- `ENCRYPTION_KEY`: Key for encrypting API keys

## API Endpoints

- `/api/v1/companies/*`: Company management
- `/api/v1/agents/*`: Agent creation and management
- `/api/v1/tokens/*`: Token generation
- `/api/v1/usage/*`: Usage statistics
- `/api/v1/billing/*`: Billing information

## Project Structure

```
voice-agent-multi-tenant-system/
├── api/                  # API routes and controllers
├── core/                 # Core business logic
├── db/                   # Database models and migrations
├── models/               # Data models
├── services/             # Services for various components
├── utils/                # Utility functions
├── web/                  # Web interface
├── .env.example          # Example environment variables
├── main.py               # Application entry point
├── README.md             # This file
└── requirements.txt      # Python dependencies
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 