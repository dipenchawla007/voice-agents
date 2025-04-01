# Voice Agent System Documentation

This documentation explains the LangGraph-powered voice agent system integrated with LiveKit for real-time voice conversations.

## Overview

Our voice agent system combines the power of LangGraph for conversation flow management with LiveKit Agents SDK for high-quality voice processing. This integration creates a structured, reliable voice AI system that can handle complex customer support scenarios.

## Key Components

### Voice Agent Architecture

The system uses a multi-layer architecture:

```
┌────────────────────────────────────┐
│          LiveKit Agents SDK        │
│  (Voice processing, TTS, STT, etc) │
└───────────────────┬────────────────┘
                    │
    ┌───────────────▼───────────────┐
    │     LangGraph Integration     │
    │  (Conversation flow control)  │
    └───────────────┬───────────────┘
                    │
┌────────────────────────────────────┐
│      Voice Agent Implementations    │
│ (Greeter, Billing, Technical, etc) │
└────────────────────────────────────┘
```

### Agent Types

The system supports multiple specialized agent types:

1. **Greeter Agent**: First point of contact for customers
2. **Billing Agent**: Handles payment issues and refunds
3. **Technical Agent**: Resolves product and service issues
4. **General Agent**: Provides information and answers questions
5. **Escalation Agent**: Handles complex issues requiring management intervention

### LangGraph Integration

The LangGraph controller manages conversation flow through a state graph with nodes for:

- Intent analysis
- Customer verification
- Knowledge base search
- Sentiment analysis
- Agent routing
- Response generation

## Benefits

1. **Structured Conversations**
   - Graph-based flow control
   - Explicit state transitions
   - Predictable agent behavior

2. **Improved Voice Experience**
   - Agent-specific voice selection
   - Sentiment-aware responses
   - Natural conversation flow

3. **Enhanced Security**
   - Multi-tenant isolation
   - Identity verification for sensitive operations
   - Permission-based access control

4. **Better Performance**
   - Optimal LLM usage
   - Cached intermediate results
   - Parallel processing where possible

## How to Use

### Running the Voice Agent System

To start the LangGraph-enabled voice agent system:

```bash
python -m services.voice.langgraph_main
```

### Development and Customization

To create new agent types or modify existing ones:

1. Extend `BaseAgent` class in `services/voice/base_agent.py`
2. Add agent-specific function tools
3. Register the new agent in `agent_factory.py`

To modify the conversation flow:

1. Update the graph structure in `graph_controller.py`
2. Add or modify nodes as needed
3. Update the routing logic between nodes 