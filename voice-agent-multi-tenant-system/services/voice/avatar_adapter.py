"""
Avatar integration adapter for LangGraph voice agents.

This module provides integration between the LangGraph-enabled voice agents
and the LiveKit avatar visualization system.
"""

import logging
import asyncio
from dataclasses import asdict, dataclass
from typing import Optional, Dict, Any

import httpx
from livekit import api, rtc
from livekit.agents import JobContext
from livekit.agents.voice.avatar import DataStreamAudioOutput
from livekit.agents.voice.room_io import ATTRIBUTE_PUBLISH_ON_BEHALF

logger = logging.getLogger("avatar-voice-agent")

@dataclass
class AvatarConnectionInfo:
    room_name: str
    url: str  # LiveKit server URL
    token: str  # Token for avatar worker to join

class AvatarAdapter:
    """Adapter to integrate avatar visualization with voice agents."""
    
    def __init__(self, avatar_dispatcher_url: str = "http://localhost:8089/launch"):
        """Initialize the avatar adapter.
        
        Args:
            avatar_dispatcher_url: URL of the avatar dispatcher service
        """
        self.avatar_dispatcher_url = avatar_dispatcher_url
        self.avatar_identity: Optional[str] = None
        self._session_data: Dict[str, Any] = {}
    
    async def initialize_avatar(self, ctx: JobContext, agent_identity: str) -> None:
        """Initialize the avatar worker for a given agent session.
        
        Args:
            ctx: The job context from the agent session
            agent_identity: Identity of the agent to associate with avatar
        """
        self.avatar_identity = f"avatar_{agent_identity}"
        
        # Create token for avatar worker
        token = (
            api.AccessToken()
            .with_identity(self.avatar_identity)
            .with_name("Avatar Runner")
            .with_grants(api.VideoGrants(room_join=True, room=ctx.room.name))
            .with_kind("agent")
            .with_attributes({ATTRIBUTE_PUBLISH_ON_BEHALF: agent_identity})
            .to_jwt()
        )
        
        # Send connection info to avatar dispatcher
        logger.info(f"Sending connection info to avatar dispatcher {self.avatar_dispatcher_url}")
        connection_info = AvatarConnectionInfo(
            room_name=ctx.room.name,
            url=ctx._info.url,
            token=token
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.avatar_dispatcher_url,
                json=asdict(connection_info)
            )
            response.raise_for_status()
        
        logger.info("Avatar handshake completed")
        
        # Wait for avatar worker to join
        await ctx.wait_for_participant(
            identity=self.avatar_identity,
            kind=rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
        )
        logger.info("Avatar runner joined successfully")
    
    def configure_audio_output(self, session: Any) -> None:
        """Configure the agent session to use avatar audio output.
        
        Args:
            session: The agent session to configure
        """
        if not self.avatar_identity:
            raise RuntimeError("Avatar not initialized. Call initialize_avatar first.")
            
        # Connect audio output to avatar
        session.output.audio = DataStreamAudioOutput(
            session.room,
            destination_identity=self.avatar_identity
        )
        
        # Log playback events
        @session.output.audio.on("playback_finished")
        def on_playback_finished(ev: Any) -> None:
            logger.info(
                "Avatar playback finished",
                extra={
                    "playback_position": ev.playback_position,
                    "interrupted": ev.interrupted,
                }
            )
    
    def store_session_data(self, key: str, value: Any) -> None:
        """Store session-specific data.
        
        Args:
            key: Data key
            value: Data value
        """
        self._session_data[key] = value
    
    def get_session_data(self, key: str) -> Any:
        """Retrieve session-specific data.
        
        Args:
            key: Data key to retrieve
            
        Returns:
            The stored value or None if not found
        """
        return self._session_data.get(key) 