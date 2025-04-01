"""
Main entrypoint for the voice agent system.

This module provides the main entrypoint for the multi-tenant voice agent system
using LiveKit Agents SDK.
"""

import logging
import asyncio
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
from services.voice.agent_factory import create_agents, add_routing_capabilities, get_default_agent

logger = logging.getLogger("voice-agent")
logger.setLevel(logging.INFO)

load_dotenv()

def prewarm(proc: JobProcess):
    """Preload models to improve startup performance"""
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Prewarmed voice activity detector")


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the customer support system"""
    logger.info("Starting voice agent system")
    await ctx.connect()
    
    # Initialize customer data
    customer_data = CustomerData()
    
    # Create all specialized agents
    agents = create_agents(customer_data)
    
    # Store agents in shared data for cross-agent access
    customer_data.agents = agents
    
    # Add routing capabilities for the new escalation agent
    add_routing_capabilities(agents)
    
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
    default_agent = agents[default_agent_name]
    
    logger.info(f"Starting session with {default_agent_name} agent")
    await session.start(
        agent=default_agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            dtx_enabled=True,  # Better voice quality
        ),
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,  # Enable transcription for the customer
        ),
    )
    
    logger.info("Session started successfully")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm)) 