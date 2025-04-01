# Voice Agent System

This directory contains a multi-tenant voice agent system built with the LiveKit Agents SDK. The system provides a robust customer support solution with multiple specialized agents that can handle different types of customer inquiries.

## Architecture

The voice agent system uses a multi-agent architecture where conversations can be transferred between different specialized agents based on the customer's needs:

```
                  ┌───────────────┐
                  │   Greeter     │
                  │    Agent      │
                  └───────┬───────┘
                          │
                          ▼
        ┌─────────┬───────┴────────┬─────────┐
        │         │                │         │
┌───────▼──────┐ ┌▼──────────────┐ ┌─────────▼─────┐ ┌──────────────┐
│   Billing    │ │   Technical   │ │    General    │ │  Escalation  │
│    Agent     │ │     Agent     │ │     Agent     │ │    Agent     │
└──────┬───────┘ └───────┬───────┘ └───────┬───────┘ └──────┬───────┘
        │                 │                 │                │
        │                 │                 │                │
        └─────────┬───────┴─────────┬───────┴────────┬──────┘
                  │                 │                │
                  ▼                 ▼                ▼
           Route to Greeter   Route to Escalation   Other Routes
```

## Agent Types

1. **Greeter Agent** - The first point of contact that welcomes customers and routes them to the appropriate specialist agent.

2. **Billing Agent** - Handles payment-related issues, refunds, subscription concerns, and invoice questions.

3. **Technical Agent** - Resolves product functionality issues, troubleshooting, and technical problems.

4. **General Agent** - Provides information about products, services, policies, and answers general inquiries.

5. **Escalation Agent** - Handles complex issues requiring manager intervention, special exceptions, or advanced problem-solving. This agent has capabilities beyond the standard agents:
   - Applying account exceptions
   - Escalating to human managers
   - Issuing goodwill credits
   - Creating follow-up appointments

## Key Features

- **Multi-tenant Design** - The system supports multiple companies with isolated configurations.
- **Context Sharing** - Customer information and conversation history is shared across agents.
- **Security Verification** - Sensitive operations require customer verification.
- **Voice Optimization** - Different voices for different agent roles to create a better user experience.
- **Metrics Collection** - Usage metrics are collected for billing and optimization.

## Routing Logic

Agents can transfer the conversation to other agents based on:

1. Customer needs (billing, technical, general information)
2. Issue complexity (escalation to manager)
3. Special handling requirements (policy exceptions, complex refunds)

The Escalation Agent specifically handles:
- Issues requiring manager approval
- Exceptions to standard policies
- Special accommodations or goodwill gestures
- Complex problems that other agents can't solve

## Usage

To run the voice agent system:

```bash
python -m services.voice.main
```

## Implementation Details

- LiveKit Agents SDK for real-time voice communication
- OpenAI models for natural language understanding and generation
- Deepgram for speech-to-text transcription
- Silero for voice activity detection
- Customizable per-agent prompts and capabilities