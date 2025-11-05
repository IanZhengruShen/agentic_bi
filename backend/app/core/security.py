"""
Security utilities for authentication.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import hashlib
import uuid

from app.core.config import settings

# Password hashing context with explicit bcrypt configuration
# Using ident="2b" for maximum compatibility with bcrypt 4.x
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",
    bcrypt__rounds=12
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate bcrypt password hash.

    Args:
        password: Plain text password

    Returns:
        str: Bcrypt hashed password
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password meets strength requirements.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Args:
        password: Password to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt.jwt_expiration_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": str(uuid.uuid4())  # Add unique JWT ID for token tracking
    })

    return jwt.encode(to_encode, settings.jwt.jwt_secret, algorithm=settings.jwt.jwt_algorithm)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Payload data to encode (typically just user_id)

    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt.jwt_refresh_expiration_days)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": str(uuid.uuid4())  # Add unique JWT ID to prevent duplicate tokens
    })

    return jwt.encode(to_encode, settings.jwt.jwt_secret, algorithm=settings.jwt.jwt_algorithm)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token to decode

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.jwt.jwt_secret, algorithms=[settings.jwt.jwt_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def hash_token(token: str) -> str:
    """
    Hash a token for storage using SHA-256.

    Used for storing refresh tokens in database.

    Args:
        token: Token to hash

    Returns:
        str: SHA-256 hash of token
    """
    return hashlib.sha256(token.encode()).hexdigest()
