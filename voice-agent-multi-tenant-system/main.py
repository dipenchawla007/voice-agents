"""
Voice Agent Multi-Tenant System
Main FastAPI application entry point
"""
import os
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.router import api_router
from utils.logging import setup_logging
from db.schemas import create_tables

# Setup logging
logger = setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Voice Agent Multi-Tenant API",
    description="API for managing voice agents across multiple companies",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "version": app.version
    }

@app.get("/", tags=["root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint
    """
    return {
        "message": "Welcome to Voice Agent Multi-Tenant API",
        "docs_url": "/docs",
        "version": app.version
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )

@app.on_event("startup")
async def startup():
    """
    Application startup event handler
    """
    # Create database tables
    await create_tables()
    logger.info("Application started, database tables created")

@app.on_event("shutdown")
async def shutdown():
    """
    Application shutdown event handler
    """
    logger.info("Application shutting down")

if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "development") == "development"
    ) 