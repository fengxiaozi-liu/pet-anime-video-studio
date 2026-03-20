"""
Security Module Tests

Tests for HTTP Basic Auth, rate limiting, and access control.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from app.security import SecurityManager


class TestSecurityManager:
    """Test cases for SecurityManager class."""

    @pytest.fixture
    def security_manager(self):
        """Create a security manager with default settings for testing."""
        return SecurityManager(
            api_keys={"test_user": "password123"},
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=20
        )

    def test_authenticate_success(self, security_manager):
        """Test successful authentication."""
        from fastapi.security import HTTPBasicCredentials
        
        credentials = HTTPBasicCredentials(username="test_user", password="password123")
        result = security_manager.authenticate(credentials)
        
        assert result == "test_user"

    def test_authenticate_failure(self, security_manager):
        """Test failed authentication raises exception."""
        from fastapi.security import HTTPBasicCredentials
        
        credentials = HTTPBasicCredentials(username="test_user", password="wrong_password")
        
        with pytest.raises(HTTPException) as exc_info:
            security_manager.authenticate(credentials)
        
        assert exc_info.value.status_code == 401

    def test_rate_limit_passed(self, security_manager):
        """Test that requests within limit are allowed."""
        user_id = "test_user_1"
        
        # Add user to API keys
        security_manager.api_keys[user_id] = "password"
        
        # Should pass - first 5 requests within minute limit
        for _ in range(5):
            allowed, headers = security_manager.check_rate_limit(user_id)
            assert allowed is True

    def test_rate_limit_exceeded(self, security_manager):
        """Test that requests exceeding limit are blocked."""
        user_id = "test_user_2"
        security_manager.api_keys[user_id] = "password"
        
        # Exceed the per-minute limit (5 req/min)
        for _ in range(5):
            security_manager.check_rate_limit(user_id)
        
        # This request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            security_manager.check_rate_limit(user_id)
        
        assert exc_info.value.status_code == 429

    def test_different_users_independent_limits(self, security_manager):
        """Test that different users have independent rate limits."""
        user1 = "user_a"
        user2 = "user_b"
        security_manager.api_keys[user1] = "password"
        security_manager.api_keys[user2] = "password"
        
        # Exhaust user1's limit
        for _ in range(5):
            security_manager.check_rate_limit(user1)
        
        # user1 should be blocked
        with pytest.raises(HTTPException):
            security_manager.check_rate_limit(user1)
        
        # user2 should still be allowed
        allowed, _ = security_manager.check_rate_limit(user2)
        assert allowed is True

    def test_disabled_mode_always_allows(self):
        """Test that disabled mode bypasses all checks."""
        security = SecurityManager(api_keys={}, enabled=False)
        
        user_id = "any_user"
        
        # Should always allow regardless of request count
        for _ in range(100):
            allowed, _ = security.check_rate_limit(user_id)
            assert allowed is True

    def test_reset_limits(self, security_manager):
        """Test resetting rate limits for a user."""
        user_id = "reset_test_user"
        security_manager.api_keys[user_id] = "password"
        
        # Exhaust the limit
        for _ in range(5):
            security_manager.check_rate_limit(user_id)
        
        # Should be blocked now
        with pytest.raises(HTTPException):
            security_manager.check_rate_limit(user_id)
        
        # Reset limits
        security_manager.reset_limits(user_id)
        
        # Should be allowed again
        allowed, _ = security_manager.check_rate_limit(user_id)
        assert allowed is True

    def test_statistics_initialization(self, security_manager):
        """Test that statistics are properly initialized."""
        # Check that rate_limits dict exists
        assert hasattr(security_manager, 'rate_limits')
        assert callable(security_manager.check_rate_limit)
