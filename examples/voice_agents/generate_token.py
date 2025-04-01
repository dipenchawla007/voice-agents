#!/usr/bin/env python3
import datetime
import os
import jwt
import time
import argparse

def generate_livekit_token(api_key, api_secret, room_name, identity="basic_user", ttl_hours=24):
    """
    Generate a LiveKit token with extended validity
    
    Args:
        api_key: Your LiveKit API key
        api_secret: Your LiveKit API secret
        room_name: The room to join
        identity: Identity of the participant
        ttl_hours: How many hours the token should be valid for
    
    Returns:
        JWT token string
    """
    # Calculate expiration time
    now = int(time.time())
    exp = now + (ttl_hours * 3600)  # Convert hours to seconds
    
    # Create the claims for the token
    claims = {
        "iss": api_key,  # Issuer - your API key
        "nbf": now,      # Not before - now
        "exp": exp,      # Expiration time
        "sub": identity, # Subject - the participant identity
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True
        }
    }
    
    # Generate the JWT token
    token = jwt.encode(claims, api_secret, algorithm="HS256")
    return token

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate a LiveKit token for a specific room')
    parser.add_argument('--room', type=str, default="test-room", help='Name of the room to join (default: test-room)')
    args = parser.parse_args()
    
    # Get API credentials from environment or use defaults
    api_key = os.environ.get("LIVEKIT_API_KEY", "APImzrsdeJDUv4U")
    api_secret = os.environ.get("LIVEKIT_API_SECRET", "8zPb6As8PsJ12ct4f8dMi6JB4V12zViTIXsMxNuPlKL")
    livekit_url = os.environ.get("LIVEKIT_URL", "wss://podcast-xad65nds.livekit.cloud")
    
    # Generate token for the specified room
    room_name = args.room
    token = generate_livekit_token(api_key, api_secret, room_name, identity="basic_user", ttl_hours=24)
    
    print(f"LiveKit URL: {livekit_url}")
    print(f"Room Name: {room_name}")
    print(f"Token (valid for 24 hours):")
    print(token)
    
    # Print command to use the token with basic_agent.py
    print("\nUse this command to connect:")
    print(f"python3 basic_agent.py connect --url \"{livekit_url}\" --room \"{room_name}\" --api-key \"{api_key}\" --api-secret \"{api_secret}\"")
    
    print("\nAnd paste this token in the browser interface:")
    print(token) 