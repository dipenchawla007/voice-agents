"""
Service for managing company API keys and secrets
"""
import os
import hmac
import hashlib
import base64
import logging
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from utils.logging import get_logger
from utils.security.encryption import encrypt_data, decrypt_data

logger = get_logger(__name__)

class CompanyKeyManager:
    """
    Manages API keys and service keys for companies
    
    Responsibilities:
    - Generate secure API keys for companies
    - Store and retrieve encrypted service keys (OpenAI, LiveKit, etc.)
    - Validate API keys
    """
    
    def __init__(self):
        """Initialize the key manager"""
        self.key_prefix = "vapi"  # Prefix for generated API keys
        self.key_length = 32  # Length of random part of API key
    
    def generate_api_key(self, company_id: str) -> str:
        """
        Generate a secure API key for a company
        
        Args:
            company_id: ID of the company
            
        Returns:
            A securely generated API key
        """
        # Generate random bytes
        random_bytes = secrets.token_bytes(self.key_length)
        
        # Create an HMAC of the company ID with the random bytes as the key
        h = hmac.new(random_bytes, company_id.encode(), hashlib.sha256)
        hmac_digest = h.digest()
        
        # Encode both the random bytes and the HMAC
        encoded_key = base64.urlsafe_b64encode(random_bytes).decode().rstrip('=')
        encoded_hmac = base64.urlsafe_b64encode(hmac_digest).decode().rstrip('=')
        
        # Combine with prefix to create the final key
        api_key = f"{self.key_prefix}_{encoded_key}_{encoded_hmac}"
        
        logger.info(f"Generated new API key for company {company_id}")
        return api_key
    
    def store_service_key(
        self,
        company_id: str,
        service_name: str,
        key_value: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Encrypt and store a service key
        
        Args:
            company_id: ID of the company
            service_name: Name of the service (e.g., 'openai', 'livekit')
            key_value: The actual key/secret to encrypt
            metadata: Optional metadata to store with the key
            
        Returns:
            ID of the stored key
        """
        # Create key data to encrypt
        key_data = {
            "company_id": company_id,
            "service": service_name,
            "value": key_value,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Encrypt the key data
        encrypted_data = encrypt_data(str(key_data))
        
        # In a real implementation, you would store this in the database
        # Here we just return the encrypted data
        logger.info(f"Stored encrypted key for service {service_name} for company {company_id}")
        
        return encrypted_data
    
    def retrieve_service_key(self, encrypted_key: str) -> Dict[str, Any]:
        """
        Decrypt and retrieve a service key
        
        Args:
            encrypted_key: The encrypted key data
            
        Returns:
            The decrypted key data
        """
        # Decrypt the key data
        try:
            decrypted_data = decrypt_data(encrypted_key)
            
            # Parse the decrypted data
            # In a real implementation, this would be properly parsed from JSON
            # Here we're just evaluating the string representation of the dict
            key_data = eval(decrypted_data)
            
            logger.info(f"Retrieved key for service {key_data.get('service')} for company {key_data.get('company_id')}")
            
            return key_data
        except Exception as e:
            logger.error(f"Error retrieving service key: {str(e)}")
            raise ValueError("Invalid or corrupted service key")
    
    def validate_key_format(self, api_key: str) -> bool:
        """
        Validate that a key has the correct format
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if the format is valid, False otherwise
        """
        # Check prefix
        if not api_key.startswith(f"{self.key_prefix}_"):
            return False
        
        # Check parts
        parts = api_key.split("_")
        if len(parts) != 3:
            return False
        
        # Basic format validation passed
        return True

# Create a singleton instance
company_key_manager = CompanyKeyManager() 