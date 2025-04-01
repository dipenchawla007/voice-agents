"""
LiveKit token generation and management service
"""
import os
import logging
import time
import jwt
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from livekit import AccessToken, TokenVerifier

from utils.logging import get_logger

logger = get_logger(__name__)

class TokenService:
    """LiveKit token generation and management service"""
    
    def __init__(self):
        """Initialize the token service with LiveKit configuration"""
        self.livekit_url = os.getenv("LIVEKIT_URL", "wss://your-livekit-server.livekit.cloud")
        self.api_key = os.getenv("LIVEKIT_API_KEY", "")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET", "")
        
        # Validate configuration
        if not self.api_key or not self.api_secret:
            logger.warning("LiveKit API key or secret not configured")
    
    def generate_room_token(
        self,
        company_id: str,
        agent_id: str,
        user_id: Optional[str] = None,
        ttl: int = 3600  # 1 hour
    ) -> Tuple[str, str]:
        """
        Generate a LiveKit token for a user to join a room
        
        Args:
            company_id: The company ID
            agent_id: The agent ID
            user_id: Optional user ID (will generate one if not provided)
            ttl: Token time-to-live in seconds
            
        Returns:
            Tuple of (token, room_name)
        """
        # Generate a room name based on company and agent
        room_name = f"{company_id}-{agent_id}"
        
        # Use provided user_id or generate a random one
        participant_identity = user_id or f"user-{str(uuid4())[:8]}"
        
        # Create an access token
        token = AccessToken(self.api_key, self.api_secret)
        
        # Set token information
        token.add_grant(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True
        )
        
        # Set identity and TTL
        token.identity = participant_identity
        token.set_ttl(ttl)
        
        # Generate the token
        jwt_token = token.to_jwt()
        
        logger.info(f"Generated user token for room: {room_name}, identity: {participant_identity}")
        
        return jwt_token, room_name
    
    def generate_agent_token(
        self,
        company_id: str,
        agent_id: str,
        ttl: int = 86400  # 24 hours
    ) -> Tuple[str, str]:
        """
        Generate a LiveKit token for an agent to join a room
        
        Args:
            company_id: The company ID
            agent_id: The agent ID
            ttl: Token time-to-live in seconds
            
        Returns:
            Tuple of (token, room_name)
        """
        # Generate a room name based on company and agent
        room_name = f"{company_id}-{agent_id}"
        
        # Create a participant identity based on the agent ID
        participant_identity = f"agent-{agent_id}"
        
        # Create an access token
        token = AccessToken(self.api_key, self.api_secret)
        
        # Set token information with more permissions for agents
        token.add_grant(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            room_admin=True  # Agents get admin rights in rooms
        )
        
        # Set identity and TTL
        token.identity = participant_identity
        token.set_ttl(ttl)
        
        # Generate the token
        jwt_token = token.to_jwt()
        
        logger.info(f"Generated agent token for room: {room_name}, identity: {participant_identity}")
        
        return jwt_token, room_name
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a LiveKit token
        
        Args:
            token: The JWT token to validate
            
        Returns:
            Dict of token claims
            
        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            # Verify and decode the token
            verifier = TokenVerifier(self.api_key, self.api_secret)
            claims = verifier.verify(token)
            
            # Check if token is expired
            if "exp" in claims and claims["exp"] < time.time():
                raise ValueError("Token has expired")
            
            return claims
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise ValueError(f"Token validation error: {str(e)}")

# Create a singleton instance
token_service = TokenService() 