#!/usr/bin/env python3
"""
Database initialization script for creating initial data
"""
import os
import asyncio
import logging
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from db.schemas import async_session, create_tables, drop_tables
from models.company import create_company
from models.agent import create_agent
from services.company_key_manager import company_key_manager
from utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

async def init_admin_company():
    """Create an admin company with default credentials"""
    admin_email = os.getenv("SUPERADMIN_EMAIL", "admin@example.com")
    
    # Generate a unique ID for the admin company
    admin_company_id = str(uuid4())
    
    # Generate API key
    api_key = company_key_manager.generate_api_key(admin_company_id)
    
    async with async_session() as session:
        # Create admin company
        company = await create_company(
            session,
            company_id=admin_company_id,
            name="System Admin",
            email=admin_email,
            tier="enterprise",
            api_key=api_key,
            status="active"
        )
        
        logger.info(f"Created admin company with ID: {admin_company_id}")
        logger.info(f"Admin API key: {api_key}")
        
        return company

async def init_demo_company():
    """Create a demo company with sample agents"""
    demo_company_id = str(uuid4())
    
    # Generate API key
    api_key = company_key_manager.generate_api_key(demo_company_id)
    
    async with async_session() as session:
        # Create demo company
        company = await create_company(
            session,
            company_id=demo_company_id,
            name="Demo Company",
            email="demo@example.com",
            tier="professional",
            api_key=api_key,
            status="active"
        )
        
        logger.info(f"Created demo company with ID: {demo_company_id}")
        logger.info(f"Demo API key: {api_key}")
        
        # Create demo agents
        agent1_id = str(uuid4())
        agent1 = await create_agent(
            session,
            agent_id=agent1_id,
            company_id=demo_company_id,
            name="Customer Support Agent",
            description="A helpful customer support agent for product inquiries",
            voice={
                "provider": "openai",
                "voice_id": "nova",
                "language": "en-US"
            },
            llm_config={
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.7
            },
            asr_config={
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en-US"
            },
            system_prompt="You are a friendly and efficient customer support agent for Demo Company. Help customers with their inquiries about our products, focusing on clear explanations and helpful solutions.",
            greeting="Hello! I'm your Demo Company support agent. How can I assist you today?"
        )
        
        logger.info(f"Created demo agent: {agent1_id}, {agent1.name}")
        
        agent2_id = str(uuid4())
        agent2 = await create_agent(
            session,
            agent_id=agent2_id,
            company_id=demo_company_id,
            name="Sales Assistant",
            description="A persuasive sales assistant focused on product recommendations",
            voice={
                "provider": "openai",
                "voice_id": "echo",
                "language": "en-US"
            },
            llm_config={
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.8
            },
            asr_config={
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en-US"
            },
            system_prompt="You are a knowledgeable and persuasive sales assistant for Demo Company. Help customers find the right products based on their needs, highlighting key features and benefits.",
            greeting="Hi there! I'm your Demo Company sales assistant. Looking for product recommendations? I'm here to help!"
        )
        
        logger.info(f"Created demo agent: {agent2_id}, {agent2.name}")
        
        return company

async def create_initial_data():
    """Create initial data in the database"""
    logger.info("Creating initial database data...")
    
    try:
        # Create admin company
        admin_company = await init_admin_company()
        
        # Create demo company with agents
        demo_company = await init_demo_company()
        
        logger.info("Initial database data created successfully")
    except Exception as e:
        logger.error(f"Error creating initial data: {str(e)}")
        raise

async def init_database(reset: bool = False):
    """Initialize the database"""
    logger.info("Initializing database...")
    
    try:
        if reset:
            # Drop all tables first
            await drop_tables()
            logger.info("Dropped all existing tables")
        
        # Create tables
        await create_tables()
        logger.info("Created database tables")
        
        # Create initial data
        await create_initial_data()
        
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Set up logging
    setup_logging()
    
    # Get reset flag from environment
    reset_db = os.getenv("RESET_DB", "false").lower() == "true"
    
    # Run database initialization
    asyncio.run(init_database(reset=reset_db)) 