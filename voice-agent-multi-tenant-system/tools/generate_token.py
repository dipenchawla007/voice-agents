#!/usr/bin/env python3
"""
Command-line tool for generating LiveKit tokens manually
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.livekit.token_service import token_service
from utils.logging import setup_logging

logger = setup_logging()

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Generate LiveKit tokens for voice agents")
    
    # Token type (user or agent)
    parser.add_argument("--type", choices=["user", "agent"], default="user",
                        help="Type of token to generate (user or agent)")
    
    # Required arguments
    parser.add_argument("--company-id", required=True, help="Company ID")
    parser.add_argument("--agent-id", required=True, help="Agent ID")
    
    # Optional arguments
    parser.add_argument("--user-id", help="User ID (for user tokens)")
    parser.add_argument("--ttl", type=int, help="Token time-to-live in seconds")
    
    # API key and secret (can be provided via environment variables)
    parser.add_argument("--api-key", help="LiveKit API key")
    parser.add_argument("--api-secret", help="LiveKit API secret")
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    # If API key and secret are provided, use them temporarily
    if args.api_key and args.api_secret:
        original_api_key = token_service.api_key
        original_api_secret = token_service.api_secret
        
        token_service.api_key = args.api_key
        token_service.api_secret = args.api_secret
    
    try:
        if args.type == "user":
            # Generate user token
            token, room_name = token_service.generate_room_token(
                company_id=args.company_id,
                agent_id=args.agent_id,
                user_id=args.user_id,
                ttl=args.ttl or 3600  # Default 1 hour
            )
            token_type = "User"
            ttl = args.ttl or 3600
            
        else:
            # Generate agent token
            token, room_name = token_service.generate_agent_token(
                company_id=args.company_id,
                agent_id=args.agent_id,
                ttl=args.ttl or 86400  # Default 24 hours
            )
            token_type = "Agent"
            ttl = args.ttl or 86400
        
        # Print the result
        print("\n=== Voice Agent Token ===")
        print(f"Type:      {token_type}")
        print(f"Company:   {args.company_id}")
        print(f"Agent:     {args.agent_id}")
        if args.type == "user" and args.user_id:
            print(f"User:      {args.user_id}")
        print(f"Room:      {room_name}")
        print(f"Expires:   {ttl} seconds")
        print(f"URL:       {token_service.livekit_url}")
        print("\nToken:")
        print(token)
        print("\n=========================")
        
    except Exception as e:
        print(f"Error generating token: {e}")
        return 1
    
    finally:
        # Restore original API key and secret if they were changed
        if args.api_key and args.api_secret:
            token_service.api_key = original_api_key
            token_service.api_secret = original_api_secret
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 