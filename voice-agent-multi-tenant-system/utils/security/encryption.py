"""
Encryption utilities for secure storage of API keys and secrets
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

def get_encryption_key() -> bytes:
    """
    Get the encryption key for Fernet symmetric encryption
    Uses environment variable or derives a key from a secret
    
    Returns:
        Fernet-compatible key as bytes
    """
    # Try to get key directly from environment
    env_key = os.getenv("ENCRYPTION_KEY")
    
    if env_key:
        # If provided directly, ensure it's properly formatted
        try:
            # Try to decode it to ensure it's valid
            if len(env_key) % 4 != 0:
                # Add padding if needed
                env_key += "=" * (4 - len(env_key) % 4)
            decoded = base64.urlsafe_b64decode(env_key)
            if len(decoded) == 32:  # Valid Fernet key is 32 bytes
                return env_key.encode()
        except Exception as e:
            logger.warning(f"Invalid encryption key provided in environment: {e}")
    
    # If no valid key in environment, derive one from JWT secret
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise ValueError("No encryption key or JWT secret found in environment")
    
    # Use PBKDF2 to derive a key from the JWT secret
    salt = b"voiceagent_encryption_salt"  # Fixed salt for deterministic derivation
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(jwt_secret.encode()))
    
    logger.info("Derived encryption key from JWT secret")
    return key

def encrypt_data(data: str, key: bytes = None) -> str:
    """
    Encrypt a string using Fernet symmetric encryption
    
    Args:
        data: The string to encrypt
        key: Optional encryption key, gets from environment if not provided
        
    Returns:
        Encrypted data as a string
    """
    if key is None:
        key = get_encryption_key()
    
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return encrypted.decode()

def decrypt_data(encrypted_data: str, key: bytes = None) -> str:
    """
    Decrypt a string using Fernet symmetric encryption
    
    Args:
        encrypted_data: The encrypted string to decrypt
        key: Optional encryption key, gets from environment if not provided
        
    Returns:
        Decrypted data as a string
    """
    if key is None:
        key = get_encryption_key()
    
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_data.encode())
    return decrypted.decode() 