"""Security module for Pet Anime Video Backend.

Provides:
- API Key Authentication
- Rate Limiting (sliding window algorithm)
- Request validation
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Rate limiting state per API key."""
    request_times: list[float] = field(default_factory=list)
    last_reset: float = field(default_factory=time.time)


class SecurityManager:
    """Manages API authentication and rate limiting."""
    
    def __init__(
        self,
        api_keys: dict[str, str],  # username -> password
        requests_per_minute: int = 10,
        requests_per_hour: int = 100,
        enabled: bool = True,
    ):
        self.api_keys = api_keys
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.enabled = enabled
        
        # Rate limit tracking: {username: RateLimitState}
        self.rate_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)
        
        logger.info(f"SecurityManager initialized: enabled={enabled}, "
                   f"RPM={requests_per_minute}, RPH={requests_per_hour}")
    
    def authenticate(self, credentials: HTTPBasicCredentials) -> str | None:
        """Authenticate using HTTP Basic auth.
        
        Returns:
            Username if authenticated, None otherwise.
            
        Raises:
            HTTPException: If authentication fails or is disabled.
        """
        if not self.enabled:
            return credentials.username
            
        if credentials.username in self.api_keys:
            expected_password = self.api_keys[credentials.username]
            # Constant-time comparison to prevent timing attacks
            if hmac.compare_digest(credentials.password, expected_password):
                logger.info(f"Authentication successful for user: {credentials.username}")
                return credentials.username
        
        logger.warning(f"Authentication failed for user: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    def check_rate_limit(self, username: str) -> tuple[bool, dict[str, Any]]:
        """Check if request is within rate limits.
        
        Args:
            username: The authenticated user's name.
            
        Returns:
            Tuple of (is_allowed, rate_limit_headers).
            
        Raises:
            HTTPException: If rate limit exceeded.
        """
        if not self.enabled:
            return True, {}
            
        now = time.time()
        state = self.rate_limits[username]
        
        # Clean old requests (older than 1 hour)
        one_hour_ago = now - 3600
        state.request_times = [t for t in state.request_times if t > one_hour_ago]
        
        # Count requests in the last minute
        one_minute_ago = now - 60
        recent_requests = [t for t in state.request_times if t > one_minute_ago]
        
        # Check limits
        minute_count = len(recent_requests)
        hour_count = len(state.request_times)
        
        headers = {
            "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
            "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Minute": str(max(0, self.requests_per_minute - minute_count - 1)),
            "X-RateLimit-Remaining-Hour": str(max(0, self.requests_per_hour - hour_count - 1)),
        }
        
        if minute_count >= self.requests_per_minute:
            retry_after = 60 - (now - recent_requests[-1])
            headers["Retry-After"] = str(int(retry_after) + 1)
            logger.warning(f"Rate limit exceeded (minute) for user: {username}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers=headers,
            )
            
        if hour_count >= self.requests_per_hour:
            headers["Retry-After"] = "3600"
            logger.warning(f"Rate limit exceeded (hour) for user: {username}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_hour} requests per hour.",
                headers=headers,
            )
        
        # Record this request
        state.request_times.append(now)
        return True, headers
    
    def record_request(self, username: str) -> None:
        """Record a request for rate limiting (already done in check_rate_limit).
        
        This method is kept for backwards compatibility but is deprecated.
        """
        pass
    
    def reset_limits(self, username: str) -> None:
        """Reset rate limits for a user (for testing/admin purposes)."""
        self.rate_limits[username] = RateLimitState()
        logger.info(f"Rate limits reset for user: {username}")


# Global dependency function
async def get_current_user(
    credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
    request: Request = None,
) -> str | None:
    """Dependency to get the current authenticated user.
    
    Can be used as: current_user: str = Depends(get_current_user)
    
    Returns:
        Username string if authenticated, None if security is disabled.
        
    Raises:
        HTTPException: If authentication fails.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    from .main import security_manager
    
    username = security_manager.authenticate(credentials)
    _, headers = security_manager.check_rate_limit(username)
    
    # Log the request with rate limit info
    logger.debug(f"Request from {username}: {request.method} {request.url.path}")
    
    return username


def generate_api_key(secret: str) -> str:
    """Generate a hashed API key from a secret string.
    
    Args:
        secret: A secret string (password) to hash.
        
    Returns:
        SHA256 hex digest of the secret.
    """
    return hashlib.sha256(secret.encode()).hexdigest()
