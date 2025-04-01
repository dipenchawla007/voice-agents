# LangGraph Integration for Voice Agents

This document explains how LangGraph has been integrated with our LiveKit voice agents to create a more powerful, efficient, and maintainable customer support system.

## Architecture Overview

The LangGraph integration adds a sophisticated conversation flow management layer on top of LiveKit's voice agent capabilities:

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

## Key Components

1. **GraphController** (`graph_controller.py`)
   - Manages the state graph for conversation flows
   - Defines nodes for each conversation stage
   - Handles transitions between conversation stages
   - Implements business logic for routing decisions

2. **LangGraphAdapter** (`langgraph_adapter.py`)
   - Bridges between LiveKit agents and LangGraph
   - Maps LiveKit sessions to LangGraph sessions
   - Passes messages between systems
   - Maintains cross-session state

3. **LangGraphEnabledAgent** (`langgraph_adapter.py`)
   - Wrapper that enhances any LiveKit agent with LangGraph capabilities
   - Delegates message processing to the graph controller
   - Maintains compatibility with existing agent code

4. **LangGraphGreeterAgent** (`langgraph_modified_agent.py`)
   - Direct LangGraph integration example
   - Uses LangGraph controller for enhanced decision-making
   - Demonstrates how to use LangGraph for complex routing decisions

5. **LangGraph Main Entrypoint** (`langgraph_main.py`)
   - Sets up the LangGraph-enabled voice agent system
   - Initializes the adapter and wraps base agents
   - Maintains the same LiveKit voice capabilities

## Conversation Flow Graph

The LangGraph controller implements a state graph with the following nodes:

```
                  ┌─────────────────┐
                  │  analyze_intent │
                  └────────┬────────┘
                           │
                           ▼
   ┌──────────────┬────────┴────────┬──────────────┐
   │              │                 │              │
┌──▼───┐    ┌─────▼─────┐    ┌──────▼─────┐  ┌─────▼──────┐
│verify│    │knowledge_ │    │route_to_   │  │process_    │
│_user │    │search     │    │agent       │  │response    │
└──┬───┘    └─────┬─────┘    └──────┬─────┘  └─────┬──────┘
   │              │                 │              │
   └──────────────┼─────────────────┼──────────────┘
                  │                 │
           ┌──────▼──────┐          │
           │ analyze_    │          │
           │ sentiment   │          │
           └──────┬──────┘          │
                  │                 │
                  └─────────────────┘
```

Each node performs a specific function within the conversation:

- **analyze_intent**: Determines what the customer wants and whether verification is needed
- **verify_customer**: Handles identity verification for security-sensitive requests
- **knowledge_search**: Retrieves relevant information for the agent's response
- **analyze_sentiment**: Detects customer emotions to adjust response tone
- **route_to_agent**: Transfers conversation to the appropriate specialist
- **process_agent_response**: Generates the agent's response using the current context

## Key Benefits

### 1. Structured Conversation Flows

- **Graph-based structure**: Explicit nodes and edges control conversation flow
- **Deterministic behavior**: Predictable agent responses in all scenarios
- **Visual reasoning**: Graph structure maps directly to conversation design

### 2. Optimized Token Usage

- **Selective LLM calls**: Only invoke LLMs when necessary
- **Cached reasoning**: Save intermediate results between stages
- **Process isolation**: Handle verification, knowledge search, and response generation separately

### 3. Enhanced Decision Making

- **Multi-stage analysis**: Break complex decisions into manageable steps
- **Intelligent routing**: Use full conversation context for agent selection
- **Sentiment-aware responses**: Adapt tone based on customer emotions

### 4. Reliability and Control

- **Explicit error handling**: Each node can handle failures independently
- **Fallback mechanisms**: Built-in recovery paths for conversation breakdowns
- **Conversation replay**: Debug by tracing paths through the graph

### 5. Performance Improvements

- **Parallel processing**: Run sentiment analysis and knowledge search concurrently
- **Reduced latency**: Avoid redundant LLM calls by caching intermediate results
- **Efficient model usage**: Use smaller models for routine tasks, larger models for complex reasoning

## Usage Examples

### Using the LangGraph-Enabled System

To start the LangGraph-enabled voice agent system:

```bash
python -m services.voice.langgraph_main
```

### Using the LangGraph Adapter Directly

```python
from services.voice.langgraph_adapter import LangGraphAdapter

# Create the adapter
adapter = LangGraphAdapter(company_id="my_company")

# Process a user message
result = await adapter.process_user_message(
    message="I need help with my billing",
    livekit_session_id="session123",
    live_context=context
)
```

### Using the LangGraph Controller Directly

```python
from services.voice.graph_controller import GraphController

# Create the controller
controller = GraphController(company_id="my_company")

# Process a user message
result = await controller.process_message(
    user_message="I need help with my billing",
    session_id="graph_session_123",
    live_context=context
)
```

## Implementation Considerations

When using LangGraph with LiveKit voice agents:

1. **State Management**: Carefully design what information needs to be in the state graph
2. **Session Mapping**: Maintain reliable mapping between LiveKit sessions and graph sessions
3. **Error Handling**: Add error recovery paths in the graph for all conversation breakdowns
4. **Performance**: Consider latency impacts of additional processing steps
5. **Testing**: Test all paths through the conversation graph

## Future Enhancements

1. **Persistence**: Add database-backed MemorySaver implementations
2. **Visual Graph Editor**: Create a UI for editing conversation flows
3. **Automatic Optimization**: Use metrics to optimize conversation paths
4. **Enhanced Sentiment Analysis**: Add dedicated models for emotion detection
5. **Multi-modal Support**: Extend to handle image and document inputs 