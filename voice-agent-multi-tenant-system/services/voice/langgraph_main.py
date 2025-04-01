"""
LangGraph-enabled voice agent system entrypoint.

This module provides the main entrypoint for the LangGraph-enhanced
multi-tenant voice agent system using LiveKit Agents SDK.
"""

import logging
import asyncio
import argparse
from typing import Dict, Any

from dotenv import load_dotenv

from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
    metrics,
)
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero, turn_detector

from services.voice.base_agent import CustomerData, VOICES
from services.voice.agent_factory import create_agents, get_default_agent
from services.voice.langgraph_adapter import LangGraphAdapter, create_langgraph_enabled_agent
from services.voice.avatar_adapter import AvatarAdapter

# Set up logging
logger = logging.getLogger("langgraph-voice-agent")
logger.setLevel(logging.INFO)

load_dotenv()

def prewarm(proc: JobProcess):
    """Preload models to improve startup performance"""
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Prewarmed voice activity detector")


async def entrypoint(ctx: JobContext, avatar_dispatcher_url: str):
    """Main entrypoint for the LangGraph-enabled customer support system
    
    Args:
        ctx: Job context from LiveKit Agents SDK
        avatar_dispatcher_url: URL of the avatar dispatcher service
    """
    logger.info("Starting LangGraph-enabled voice agent system with avatar support")
    await ctx.connect()
    
    # Get company ID from context or use a default
    company_id = ctx.userdata.get("company_id", "default_company")
    
    # Create LangGraph adapter
    langgraph_adapter = LangGraphAdapter(company_id)
    
    # Create avatar adapter
    avatar_adapter = AvatarAdapter(avatar_dispatcher_url)
    
    # Initialize customer data
    customer_data = CustomerData()
    
    # Create all specialized agents
    base_agents = create_agents(customer_data)
    
    # Wrap each agent with LangGraph capabilities
    graph_enabled_agents = {
        name: create_langgraph_enabled_agent(
            agent, langgraph_adapter, company_id
        ) for name, agent in base_agents.items()
    }
    
    # Store enhanced agents in shared data for cross-agent access
    customer_data.agents = graph_enabled_agents
    
    # Create the multi-agent session
    session = AgentSession[CustomerData](
        vad=ctx.proc.userdata["vad"],
        llm=openai.LLM(model="gpt-4o-mini"),  # Default model, agents can override
        stt=deepgram.STT(model="nova-3"),     # High-accuracy speech recognition
        tts=openai.TTS(voice=VOICES[get_default_agent()]),  # Default voice from the default agent
        turn_detection=turn_detector.EOUModel(),
        userdata=customer_data,
    )
    
    # Set up usage metrics collection
    usage_collector = metrics.UsageCollector()
    
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)
    
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Session usage metrics: {summary}")
        # In a real implementation, you would store these in a database
    
    # Log usage when session ends
    ctx.add_shutdown_callback(log_usage)
    
    # Wait for a customer to join the call
    logger.info("Waiting for customer to join the call")
    await ctx.wait_for_participant()
    
    # Start with the default agent (typically the greeter)
    default_agent_name = get_default_agent()
    default_agent = graph_enabled_agents[default_agent_name]
    
    # Initialize avatar for the default agent
    await avatar_adapter.initialize_avatar(ctx, default_agent_name)
    
    # Configure avatar audio output
    avatar_adapter.configure_audio_output(session)
    
    logger.info(f"Starting session with LangGraph-enabled {default_agent_name} agent and avatar")
    await session.start(
        agent=default_agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            dtx_enabled=True,  # Better voice quality
        ),
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,  # Enable transcription for the customer
            audio_enabled=False,  # Audio will be handled by avatar
        ),
    )
    
    logger.info("Session started successfully with LangGraph and avatar integration")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--avatar-url", type=str, default="http://localhost:8089/launch")
    args, remaining_args = parser.parse_known_args()
    
    # Update sys.argv for cli.run_app
    import sys
    sys.argv = sys.argv[:1] + remaining_args
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=lambda ctx: entrypoint(ctx, args.avatar_url),
            prewarm_fnc=prewarm
        )
    ) 