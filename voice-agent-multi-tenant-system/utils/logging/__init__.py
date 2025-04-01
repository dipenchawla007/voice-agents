"""
Logging utilities for the multi-tenant voice agent system
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configure logging for the application
    Sets up console and file logging with appropriate formats
    """
    # Get log level from environment or use INFO as default
    log_level_name = os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure file handler if log directory exists
    logs_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(logs_dir):
        try:
            os.makedirs(logs_dir)
        except OSError:
            # If logs directory cannot be created, just log to console
            logging.warning("Could not create logs directory, logging to console only")
            return
    
    log_file = os.path.join(logs_dir, "voice_agents.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Add request tracking for API calls
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(log_level)
    
    # Set third-party library log levels
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized with level {log_level_name}")

def get_logger(name):
    """Get a logger for a specific module"""
    return logging.getLogger(name) 