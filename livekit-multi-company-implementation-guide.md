# LiveKit Voice Agents: Multi-Company Implementation Guide

## Table of Contents
1. [Current Implementation Overview](#current-implementation-overview)
2. [Architecture for Multi-Company Support](#architecture-for-multi-company-support)
3. [API Key Management Strategy](#api-key-management-strategy)
4. [Frontend-Backend Integration](#frontend-backend-integration)
5. [Agent Creation & Management Workflow](#agent-creation--management-workflow)
6. [Company Isolation & Access Control](#company-isolation--access-control)
7. [Usage Tracking & Billing](#usage-tracking--billing)
8. [Implementation Roadmap](#implementation-roadmap)

## Current Implementation Overview

The current LiveKit Voice Agents platform (`livekit-agents`) provides a framework for building conversational AI agents with real-time voice capabilities. The implementation includes:

### Core Components
- **Agent Framework**: Base infrastructure for voice-based agents
- **Plugin Architecture**: Modular system for integrating various AI services
- **Real-time Communication**: WebRTC-based audio/video streaming
- **Conversation Management**: Turn-taking, silence detection, interruption handling

### Available Plugins
- **Speech Services**: Deepgram, AssemblyAI, Speechmatics, Google, Azure, AWS
- **Text-to-Speech**: ElevenLabs, Neuphonic, Google, Azure, AWS
- **LLMs**: OpenAI, Anthropic, Groq, Google, Azure, AWS
- **Knowledge Base**: RAG, LlamaIndex integration, vector database support

### What's Missing for Multi-Company Support
- Company data model and isolation
- Usage tracking and quota management
- Billing and subscription handling
- Multi-tenant token management
- Administrative controls

## Architecture for Multi-Company Support

To extend the current implementation for multi-company support:

```
+---------------------+            +----------------------+            +------------------+
| Company Websites    |            | AgentStream Platform |            | LiveKit Services |
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

## API Key Management Strategy

### Required API Keys for Each Company

1. **Platform Level (Shared Infrastructure)**
   - **LiveKit API Key & Secret**: Primary credentials for LiveKit services
   - **AI Service Keys**: Optional platform-level keys for shared services

2. **Company Level (Isolation)**
   - **Company API Key**: For accessing your platform's API
   - **Room Prefixes**: `company_{id}_room_{random}`
   - **Service Quotas**: Limits on API calls, minutes, etc.

3. **Per-Service Keys (Optional BYOK Model)**
   ```json
   {
     "company_id": "company_123",
     "service_keys": {
       "openai": "sk-company123-xxxx",
       "elevenlabs": "el-company123-xxxx",
       "deepgram": "dg-company123-xxxx"
     },
     "default_model_preferences": {
       "stt_provider": "deepgram",
       "tts_provider": "elevenlabs",
       "llm_provider": "openai",
       "llm_model": "gpt-4o"
     }
   }
   ```

### Key Storage and Management

```python
class CompanyKeyManager:
    def __init__(self, db_client):
        self.db = db_client
        self.key_cache = {}
        self.vault = SecureVault()
        
    async def get_service_key(self, company_id, service_name):
        """Get the appropriate API key for a service"""
        # Check if company has own key
        company_key = await self.db.get_company_service_key(company_id, service_name)
        
        if company_key:
            # Use company's own key
            return self.vault.decrypt(company_key)
        else:
            # Use platform default key
            return await self.get_platform_key(service_name)
    
    async def get_platform_key(self, service_name):
        """Get platform default key with rate limiting"""
        # Check key usage and rate limits
        # Return appropriate platform key
```

## Frontend-Backend Integration

### Dashboard Integration

The frontend dashboard shown in your screenshots needs these backend endpoints:

```json
// GET /api/v1/companies/{company_id}/stats
{
  "total_interactions": 1245,
  "active_agents": {
    "online": 3,
    "total": 5
  },
  "conversion_rate": 24.8,
  "performance": {
    "timeline": [
      {"date": "2023-01-01", "interactions": 123},
      {"date": "2023-01-02", "interactions": 145}
    ]
  }
}
```

### Agent Management Endpoints

```
POST   /api/v1/companies/{company_id}/agents           # Create new agent
GET    /api/v1/companies/{company_id}/agents           # List agents
GET    /api/v1/companies/{company_id}/agents/{id}      # Get agent details
PUT    /api/v1/companies/{company_id}/agents/{id}      # Update agent
DELETE /api/v1/companies/{company_id}/agents/{id}      # Delete agent
```

### Widget Embed Code Generation

```javascript
// Generate unique widget code for each company
function generateWidgetCode(companyId, agentId, settings) {
  const widgetToken = generateToken(companyId, agentId);
  
  return `<script src="https://agentstream.ai/widget.js" 
          data-agent-id="${agentId}" 
          data-company-id="${companyId}"
          data-token="${widgetToken}"
          data-position="${settings.position}"
          data-color="${settings.color}"></script>`;
}
```

## Agent Creation & Management Workflow

Based on your frontend screenshots, the agent creation flow includes:

### 1. Basic Information
```python
async def create_agent(company_id, agent_data):
    """Create a new agent for a company"""
    # Validate company exists and has quota
    company = await db.get_company(company_id)
    
    if await get_agent_count(company_id) >= company.quota.max_agents:
        raise QuotaExceededError("Maximum agent limit reached")
    
    # Create agent record
    agent_id = generate_unique_id()
    agent = {
        "id": agent_id,
        "company_id": company_id,
        "name": agent_data["name"],
        "description": agent_data["description"],
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "status": "draft"
    }
    
    await db.create_agent(agent)
    return agent_id
```

### 2. Knowledge Base Management
```python
async def process_knowledge_base(company_id, agent_id, files):
    """Process and store knowledge base files"""
    # Validate permissions
    await validate_agent_ownership(company_id, agent_id)
    
    # Process each file
    for file in files:
        # Extract text from file
        text = await extract_text(file)
        
        # Split into chunks
        chunks = text_splitter.split_text(text)
        
        # Create embeddings
        embeddings = await create_embeddings(chunks)
        
        # Store in vector database with company/agent prefix
        collection_name = f"company_{company_id}_agent_{agent_id}"
        await vector_db.add_documents(collection_name, embeddings)
        
        # Update agent record
        await db.add_knowledge_source(agent_id, {
            "file_name": file.name,
            "file_type": file.content_type,
            "file_size": file.size,
            "chunk_count": len(chunks),
            "processed_at": datetime.now()
        })
```

### 3. Avatar Selection
```python
async def set_agent_avatar(company_id, agent_id, avatar_id):
    """Set the avatar for an agent"""
    # Validate permissions
    await validate_agent_ownership(company_id, agent_id)
    
    # Check if avatar is available for this company tier
    company = await db.get_company(company_id)
    avatar = await db.get_avatar(avatar_id)
    
    if avatar.tier > company.tier:
        raise PermissionError("Avatar not available in your plan")
    
    # Update agent
    await db.update_agent(agent_id, {"avatar_id": avatar_id})
    
    # Log avatar selection for billing
    await usage_tracker.log_avatar_selection(company_id, agent_id, avatar_id)
```

### 4. Widget Customization
```python
async def update_widget_config(company_id, agent_id, widget_config):
    """Update widget configuration"""
    # Validate permissions
    await validate_agent_ownership(company_id, agent_id)
    
    # Validate widget features against company tier
    company = await db.get_company(company_id)
    
    for feature in widget_config["features"]:
        if feature not in company.allowed_features:
            raise PermissionError(f"Feature {feature} not available in your plan")
    
    # Update configuration
    await db.update_agent(agent_id, {
        "widget_config": widget_config
    })
```

### 5. Deployment
```python
async def deploy_agent(company_id, agent_id):
    """Deploy an agent for production use"""
    # Validate permissions
    await validate_agent_ownership(company_id, agent_id)
    
    # Check if agent is ready to deploy
    agent = await db.get_agent(agent_id)
    
    if not agent.has_knowledge_base:
        raise ValidationError("Agent requires knowledge base")
        
    if not agent.avatar_id:
        raise ValidationError("Agent requires avatar")
    
    # Update agent status
    await db.update_agent(agent_id, {"status": "active"})
    
    # Generate embed code
    embed_code = generate_embed_code(company_id, agent_id)
    
    # Return deployment info
    return {
        "status": "active",
        "embed_code": embed_code,
        "api_endpoints": {
            "chat": f"/api/v1/public/agents/{agent_id}/chat",
            "voice": f"/api/v1/public/agents/{agent_id}/voice"
        }
    }
```

## Company Isolation & Access Control

### Company Data Model

```python
class Company:
    id: str
    name: str
    tier: str  # 'basic', 'professional', 'enterprise'
    status: str  # 'active', 'suspended', 'deleted'
    created_at: datetime
    updated_at: datetime
    
    # Quotas and Limits
    quotas: {
        "max_agents": int,
        "max_interactions_per_month": int,
        "max_minutes_per_month": int,
        "max_knowledge_base_size_mb": int,
        "max_concurrent_sessions": int
    }
    
    # Feature Access
    features: {
        "voice_enabled": bool,
        "avatar_enabled": bool,
        "multilingual": bool,
        "custom_domain": bool,
        "advanced_analytics": bool
    }
    
    # API Keys
    api_keys: List[ApiKey]
    
    # Service Keys (BYOK)
    service_keys: Dict[str, EncryptedKey]
```

### Token Generation with Isolation

```python
def generate_room_token(company_id, agent_id, user_id=None):
    """Generate a LiveKit token with company isolation"""
    # Create room name with company prefix
    room_name = f"company_{company_id}_agent_{agent_id}"
    if user_id:
        room_name += f"_user_{user_id}"
    
    # Add company metadata to token
    metadata = {
        "company_id": company_id,
        "agent_id": agent_id,
        "user_id": user_id
    }
    
    # Generate token with appropriate permissions
    token = livekit_token_service.generate_token(
        room_name=room_name,
        participant_identity=f"user_{user_id or 'anonymous'}",
        metadata=json.dumps(metadata),
        ttl_seconds=3600  # 1 hour
    )
    
    return token, room_name
```

### Permission Validation Middleware

```python
async def validate_company_permission(request, required_permission):
    """Middleware to validate company permissions"""
    # Extract company_id and API key from request
    company_id = request.path_params.get("company_id")
    api_key = request.headers.get("X-API-Key")
    
    # Validate API key belongs to company
    company = await db.get_company_by_api_key(api_key)
    if not company or company.id != company_id:
        raise HTTPException(403, "Invalid API key")
    
    # Check company status
    if company.status != "active":
        raise HTTPException(403, "Company account is not active")
    
    # Check for required permission
    if required_permission not in company.permissions:
        raise HTTPException(403, f"Missing required permission: {required_permission}")
    
    # Add company to request state
    request.state.company = company
    return True
```

## Usage Tracking & Billing

### Usage Tracking

```python
class UsageTracker:
    async def track_session(self, session_data):
        """Track a session for billing purposes"""
        # Extract session data
        company_id = session_data["company_id"]
        agent_id = session_data["agent_id"]
        user_id = session_data["user_id"]
        duration_ms = session_data["duration_ms"]
        
        # Record in database
        await self.db.insert_usage_record({
            "company_id": company_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "timestamp": datetime.now(),
            "duration_ms": duration_ms,
            "tokens_used": session_data.get("tokens_used", 0),
            "interaction_count": session_data.get("interaction_count", 0),
            "session_id": session_data["session_id"]
        })
        
        # Update aggregates
        await self.update_daily_aggregates(company_id, agent_id)
        
    async def get_company_usage(self, company_id, start_date, end_date):
        """Get usage metrics for a company in a date range"""
        return await self.db.get_company_usage(company_id, start_date, end_date)
```

### Quota Enforcement

```python
class QuotaManager:
    async def check_session_quota(self, company_id):
        """Check if company has exceeded session quota"""
        company = await self.db.get_company(company_id)
        current_month_usage = await self.usage_tracker.get_current_month_usage(company_id)
        
        # Check interaction limit
        if current_month_usage.interaction_count >= company.quotas.max_interactions_per_month:
            return {
                "allowed": False,
                "reason": "Monthly interaction limit reached",
                "limit": company.quotas.max_interactions_per_month,
                "usage": current_month_usage.interaction_count
            }
        
        # Check minutes limit
        total_minutes = math.ceil(current_month_usage.duration_ms / 60000)
        if total_minutes >= company.quotas.max_minutes_per_month:
            return {
                "allowed": False,
                "reason": "Monthly minutes limit reached",
                "limit": company.quotas.max_minutes_per_month,
                "usage": total_minutes
            }
        
        return {"allowed": True}
```

### Billing Calculation

```python
class BillingService:
    async def generate_monthly_invoice(self, company_id, year, month):
        """Generate invoice for a company"""
        company = await self.db.get_company(company_id)
        usage = await self.usage_tracker.get_monthly_usage(company_id, year, month)
        
        # Calculate base subscription cost
        base_cost = TIER_PRICING[company.tier]
        
        # Calculate usage-based costs
        usage_costs = {
            "interactions": calculate_interaction_cost(usage.interaction_count, company.tier),
            "minutes": calculate_minute_cost(usage.duration_ms / 60000, company.tier),
            "tokens": calculate_token_cost(usage.tokens_used, company.tier),
            "storage": calculate_storage_cost(usage.storage_used_mb, company.tier)
        }
        
        # Calculate total
        total_usage_cost = sum(usage_costs.values())
        total = base_cost + total_usage_cost
        
        # Create invoice
        invoice = {
            "company_id": company_id,
            "invoice_date": datetime.now(),
            "billing_period": f"{year}-{month:02d}",
            "base_subscription": base_cost,
            "usage_charges": usage_costs,
            "total": total,
            "usage_details": usage,
            "due_date": datetime.now() + timedelta(days=30)
        }
        
        await self.db.create_invoice(invoice)
        return invoice
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (1-2 months)
1. Implement company data model
2. Create token generation with company isolation
3. Develop basic usage tracking
4. Set up API key management

### Phase 2: Frontend Integration (2-3 months)
1. Integrate company dashboard
2. Implement agent creation flow
3. Develop knowledge base processing
4. Create widget customization and deployment

### Phase 3: Billing & Quotas (1-2 months)
1. Complete usage tracking and aggregation
2. Implement quota enforcement
3. Create billing calculation
4. Develop reporting and analytics

### Phase 4: Advanced Features (3-4 months)
1. Add BYOK (Bring Your Own Keys) support
2. Implement advanced analytics
3. Create administrative dashboard
4. Develop white-label options

---

This architecture enables you to provide a multi-company voice agent platform while maintaining:
- Strong isolation between companies (using room prefixes and token metadata)
- Detailed usage tracking for billing with a single LiveKit API key and secret
- Quota enforcement at various levels (company, agent, feature)
- Granular permissions management through database models
- Ability to revoke access when needed via API key management
- Comprehensive billing based on actual usage tracking

The LiveKit agents framework provides the foundation for conversational AI, while this multi-company architecture adds the business layer needed for a commercial SaaS offering.


AI Supervisor for Multi-Tenant System
Recommendations for AI Supervisor
Yes, implementing an AI Supervisor would be valuable for your multi-tenant system for several reasons:
Security Enforcement Layer: An AI Supervisor can monitor all agent interactions to prevent:
Prompt injection attempts
Cross-tenant information leakage
Policy violations
Operational Benefits:
Centralized oversight of all tenant agents
Uniform application of security policies
Detection of anomalous agent behavior
Implementation Approach:
Create a supervisor component that validates all inputs/outputs
Implement content scanning for sensitive information
Build monitoring dashboards for security operations
Current Security Practice Assessment
Your current implementation includes several good security practices:
✅ Database-level isolation through company_id filtering
✅ API authentication with company-specific API keys
✅ Service-level validation requiring company_id
✅ Token management for session authentication
However, there are opportunities for enhancement:
⚠️ Runtime monitoring of agent behavior is limited
⚠️ Content filtering for sensitive information isn't robust
⚠️ Anomaly detection for unusual access patterns is missing
⚠️ Comprehensive audit logging needs enhancement
Recommended Security Enhancements
AI Guardrails: Implement pre/post processing filters to ensure agents cannot:
Leak information across tenants
Execute unintended actions
Bypass intended security boundaries
Enhanced Monitoring:
Log all agent actions with tenant context
Implement real-time alerts for suspicious patterns
Create tenant isolation metrics
Security Testing:
Regular red-team exercises for tenant isolation
Automated testing of boundary controls
Prompt injection penetration testing

Yes, an AI Supervisor can be elegantly integrated with LangGraph as part of your multi-tenant system. Here's how it would work:


## --------
## AI Supervisor Integration with LangGraph

The AI Supervisor would be implemented as a wrapper or interceptor layer around your tenant-specific LangGraph instances:

```python
class AISupervisor:
    def __init__(self, security_config):
        self.security_config = security_config
        self.tenant_agents = {}  # Map of company_id -> LangGraph instance
    
    def create_supervised_agent(self, company_id, agent_config):
        # Create the tenant-specific LangGraph
        base_graph = create_tenant_graph(company_id, agent_config)
        
        # Wrap the graph with supervisor controls
        supervised_graph = self._add_supervisor_controls(base_graph, company_id)
        
        self.tenant_agents[company_id] = supervised_graph
        return supervised_graph
        
    def _add_supervisor_controls(self, graph, company_id):
        # Create a new graph that wraps the original
        builder = StateGraph(SupervisedState)
        
        # Add pre-execution validation node
        builder.add_node("validate_input", self._validate_input)
        
        # Add the tenant graph as a subgraph
        builder.add_subgraph("tenant_agent", graph)
        
        # Add post-execution monitoring node
        builder.add_node("security_check", self._security_check)
        
        # Connect the flow
        builder.add_edge("validate_input", "tenant_agent")
        builder.add_edge("tenant_agent", "security_check")
        
        return builder.compile()
    
    def _validate_input(self, state):
        # Pre-execution security checks
        security_issues = validate_prompt_safety(state.input, company_id=state.company_id)
        if security_issues:
            # Block or sanitize unsafe inputs
            return {"blocked": True, "reason": security_issues}
        return {"blocked": False}
    
    def _security_check(self, state):
        # Post-execution security validation
        issues = check_information_leakage(
            state.output, 
            company_id=state.company_id
        )
        if issues:
            # Redact or block problematic output
            return {"output": redact_sensitive_information(state.output, issues)}
        return {"output": state.output}
```

This approach lets you maintain the benefits of LangGraph's state management and flow control while adding centralized security enforcement. The supervisor layer can monitor all interactions, enforce tenant isolation, and prevent information leakage between companies.

The AI Supervisor becomes a critical security component that protects your multi-tenant system from various risks while providing visibility into agent behavior across all tenants.
