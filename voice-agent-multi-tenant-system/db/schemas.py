"""
Database models and connection configuration
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Text, create_engine, MetaData, Table, LargeBinary
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from utils.logging import get_logger

logger = get_logger(__name__)

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/voice_agents")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create base model class
Base = declarative_base()

metadata = MetaData()

# Company table
companies = Table(
    "companies",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("name", String(255), nullable=False),
    Column("api_key", String(255), nullable=False, unique=True),
    Column("website", String(255)),
    Column("logo_url", String(255)),
    Column("status", String(50), nullable=False, default="active"),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# Company quota table
company_quotas = Table(
    "company_quotas",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("max_interactions", Integer, nullable=False, default=1000),
    Column("max_minutes", Integer, nullable=False, default=500),
    Column("max_tokens", Integer, nullable=False, default=100000),
    Column("max_concurrent_sessions", Integer, nullable=False, default=5),
    Column("max_agents", Integer, nullable=False, default=3),
    Column("max_kb_size_mb", Integer, nullable=False, default=100),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# Agent table
agents = Table(
    "agents",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", Text),
    Column("system_prompt", Text, nullable=False),
    Column("model", String(100), nullable=False),
    Column("temperature", Float, default=0.7),
    Column("max_tokens", Integer, default=1000),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column("is_active", Boolean, nullable=False, default=True),
)

# Agent Knowledge Base Mapping
agent_kb_mapping = Table(
    "agent_kb_mapping",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("agent_id", String(36), ForeignKey("agents.id"), nullable=False),
    Column("kb_id", String(36), ForeignKey("knowledge_bases.id"), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

# Knowledge Base table
knowledge_bases = Table(
    "knowledge_bases",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", Text),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# Knowledge Base Documents
kb_documents = Table(
    "kb_documents",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("kb_id", String(36), ForeignKey("knowledge_bases.id"), nullable=False),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("filename", String(255), nullable=False),
    Column("file_type", String(50), nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("file_url", String(255), nullable=False),
    Column("status", String(50), nullable=False, default="processing"),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# Knowledge Base Chunks
kb_chunks = Table(
    "kb_chunks",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("document_id", String(36), ForeignKey("kb_documents.id"), nullable=False),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("chunk_index", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("embedding", ARRAY(Float)),
    Column("metadata", JSONB, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

# Session tracking table
sessions = Table(
    "sessions",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("agent_id", String(36), ForeignKey("agents.id"), nullable=False),
    Column("user_id", String(255)),
    Column("session_id", String(255), nullable=False),
    Column("start_time", DateTime, nullable=False),
    Column("end_time", DateTime),
    Column("duration_seconds", Integer),
    Column("total_interactions", Integer, default=0),
    Column("total_tokens", Integer, default=0),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

# Daily usage aggregates
daily_usage = Table(
    "daily_usage",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("agent_id", String(36), ForeignKey("agents.id"), nullable=True),
    Column("date", DateTime, nullable=False),
    Column("total_interactions", Integer, default=0),
    Column("total_duration_seconds", Integer, default=0),
    Column("total_tokens", Integer, default=0),
    Column("unique_users", Integer, default=0),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# API key logs
api_key_logs = Table(
    "api_key_logs",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("key_id", String(36), nullable=False),
    Column("action", String(50), nullable=False),  # created, rotated, revoked
    Column("created_by", String(255)),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("ip_address", String(50)),
    Column("user_agent", String(255)),
)

# Company data storage for integrations
company_data = Table(
    "company_data",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("data_type", String(100), nullable=False),  # customers, products, tickets, etc.
    Column("record_id", String(255), nullable=False),  # external ID of the record
    Column("data", Text, nullable=False),  # JSON data stored as text
    Column("embedding", ARRAY(Float)),  # Embedding for semantic search
    Column("is_deleted", Boolean, default=False),  # Soft delete flag
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# Company data sync status
company_data_sync = Table(
    "company_data_sync",
    metadata,
    Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("data_type", String(100), nullable=False),  # customers, products, tickets, etc.
    Column("last_sync_time", DateTime, nullable=False, default=datetime.utcnow),
    Column("record_count", Integer, default=0),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

class Company(Base):
    """Company model"""
    __tablename__ = "companies"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    tier = Column(String, default="basic")  # basic, pro, enterprise
    api_key = Column(String, unique=True)
    status = Column(String, default="active")  # active, suspended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    agents = relationship("Agent", back_populates="company", cascade="all, delete-orphan")
    quotas = relationship("CompanyQuota", uselist=False, back_populates="company", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="company", cascade="all, delete-orphan")
    usage_aggregates = relationship("UsageAggregate", back_populates="company", cascade="all, delete-orphan")

class Agent(Base):
    """Agent model"""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"))
    name = Column(String, nullable=False)
    description = Column(Text)
    voice = Column(JSON, default=lambda: {})
    llm_config = Column(JSON, default=lambda: {})
    asr_config = Column(JSON, default=lambda: {})
    knowledge_base_ids = Column(JSON, default=lambda: [])
    system_prompt = Column(Text)
    greeting = Column(Text)
    avatar_url = Column(String)
    status = Column(String, default="active")  # active, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="agents")
    usage_records = relationship("UsageRecord", back_populates="agent", cascade="all, delete-orphan")
    usage_aggregates = relationship("UsageAggregate", back_populates="agent", cascade="all, delete-orphan")

class KnowledgeBase(Base):
    """Knowledge base model"""
    __tablename__ = "knowledge_bases"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"))
    name = Column(String, nullable=False)
    description = Column(Text)
    file_count = Column(Integer, default=0)
    total_size = Column(Integer, default=0)  # Size in bytes
    status = Column(String, default="active")  # active, disabled, processing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    files = relationship("KnowledgeBaseFile", back_populates="knowledge_base", cascade="all, delete-orphan")

class KnowledgeBaseFile(Base):
    """Knowledge base file model"""
    __tablename__ = "knowledge_base_files"
    
    id = Column(String, primary_key=True)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"))
    name = Column(String, nullable=False)
    file_type = Column(String)  # pdf, txt, docx, etc.
    size = Column(Integer)  # Size in bytes
    status = Column(String, default="active")  # active, processing, error
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="files")

class CompanyQuota(Base):
    """Company quota limits model"""
    __tablename__ = "company_quotas"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), unique=True)
    max_agents = Column(Integer, default=5)
    max_knowledge_bases = Column(Integer, default=5)
    max_kb_size = Column(Integer, default=1073741824)  # 1GB in bytes
    max_concurrent_sessions = Column(Integer, default=10)
    max_monthly_interactions = Column(Integer, default=10000)
    max_monthly_minutes = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="quotas")

class UsageRecord(Base):
    """Raw usage record model"""
    __tablename__ = "usage_records"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"))
    agent_id = Column(String, ForeignKey("agents.id"))
    user_id = Column(String)  # External user ID
    session_id = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)  # Duration in seconds
    interactions = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    transcription_seconds = Column(Float, default=0)
    synthesis_characters = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="usage_records")
    agent = relationship("Agent", back_populates="usage_records")

class UsageAggregate(Base):
    """Aggregated usage metrics model"""
    __tablename__ = "usage_aggregates"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"))
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    date = Column(DateTime)
    interactions = Column(Integer, default=0)
    duration = Column(Float, default=0)  # Duration in seconds
    tokens = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    transcription_seconds = Column(Float, default=0)
    synthesis_characters = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="usage_aggregates")
    agent = relationship("Agent", back_populates="usage_aggregates")

class BillingRecord(Base):
    """Billing record model"""
    __tablename__ = "billing_records"
    
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"))
    billing_period_start = Column(DateTime)
    billing_period_end = Column(DateTime)
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")  # pending, paid, failed
    payment_method = Column(String)
    invoice_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    line_items = relationship("BillingLineItem", back_populates="billing_record", cascade="all, delete-orphan")

class BillingLineItem(Base):
    """Billing line item model"""
    __tablename__ = "billing_line_items"
    
    id = Column(String, primary_key=True)
    billing_record_id = Column(String, ForeignKey("billing_records.id"))
    description = Column(String)
    quantity = Column(Float)
    unit_price = Column(Float)
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    billing_record = relationship("BillingRecord", back_populates="line_items")

async def create_tables():
    """Create all database tables"""
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)  # Uncomment to drop all tables first
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

async def drop_tables():
    """Drop all database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped") 