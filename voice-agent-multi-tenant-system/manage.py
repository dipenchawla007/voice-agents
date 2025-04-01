#!/usr/bin/env python3
"""
Management script for the Voice Agent Multi-Tenant System
"""
import os
import sys
import argparse
import asyncio
import uvicorn

from utils.logging import setup_logging
from db.init_db import init_database


logger = setup_logging()


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Voice Agent Multi-Tenant System Management Script")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # init-db command
    init_db_parser = subparsers.add_parser("init-db", help="Initialize the database")
    init_db_parser.add_argument("--reset", action="store_true", help="Reset the database before initializing")
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run the application")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    # shell command
    subparsers.add_parser("shell", help="Open an interactive shell")
    
    return parser.parse_args()


async def init_db(reset=False):
    """Initialize the database"""
    try:
        await init_database(reset=reset)
        print("Database initialization completed successfully.")
        
        # Show admin API key from environment or a placeholder
        admin_key = os.getenv("ADMIN_API_KEY", "Check the logs for the generated admin API key")
        print(f"Admin API Key: {admin_key}")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)


def run_app(host="0.0.0.0", port=8000, reload=False):
    """Run the application"""
    try:
        print(f"Starting application on {host}:{port}")
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload
        )
    except Exception as e:
        print(f"Error running application: {e}")
        sys.exit(1)


def run_shell():
    """Run an interactive shell with loaded models and services"""
    # Set up a proper Python shell with our models and services imported
    try:
        import readline
        import code
        import rlcompleter
        
        # Import all models and services
        from db.schemas import async_session, Base
        import models.company as company_model
        import models.agent as agent_model
        from services.company_key_manager import company_key_manager
        from services.livekit.token_service import token_service
        from services.quota.manager import QuotaManager
        from services.usage_tracking.tracker import UsageTracker
        
        # Set up readline for auto-completion
        readline.parse_and_bind("tab: complete")
        
        # Create shell context
        context = {
            "async_session": async_session,
            "Base": Base,
            "company_key_manager": company_key_manager,
            "token_service": token_service,
            "QuotaManager": QuotaManager,
            "UsageTracker": UsageTracker,
            "company_model": company_model,
            "agent_model": agent_model,
        }
        
        # Start the shell
        shell = code.InteractiveConsole(context)
        shell.interact(banner="Voice Agent Multi-Tenant System Interactive Shell\n"
                      "Access company and agent functions via company_model and agent_model.")
        
    except Exception as e:
        print(f"Error starting shell: {e}")
        sys.exit(1)


def main():
    """Main function"""
    args = parse_args()
    
    if args.command == "init-db":
        asyncio.run(init_db(reset=args.reset))
    elif args.command == "run":
        run_app(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "shell":
        run_shell()
    else:
        print("No command specified. Use --help for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main() 