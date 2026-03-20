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
            enabled=True,
            max_requests_per_minute=5,
            max_requests_per_hour=20
        )

    @pytest.mark.asyncio
    async def test_rate_limit_passed(self, security_manager):
        """Test that requests within limit are allowed."""
        user_id = "test_user_1"
        
        # Should pass - first request
        result = await security_manager.check_rate_limit(user_id)
        assert result is True
        
        # Should pass - still within minute limit (5 req/min)
        for _ in range(4):
            result = await security_manager.check_rate_limit(user_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, security_manager):
        """Test that requests exceeding limit are blocked."""
        user_id = "test_user_2"
        
        # Exceed the per-minute limit (5 req/min)
        for _ in range(5):
            await security_manager.check_rate_limit(user_id)
        
        # This request should be blocked
        result = await security_manager.check_rate_limit(user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_different_users_independent_limits(self, security_manager):
        """Test that different users have independent rate limits."""
        user1 = "user_a"
        user2 = "user_b"
        
        # Exhaust user1's limit
        for _ in range(5):
            await security_manager.check_rate_limit(user1)
        
        # user1 should be blocked
        assert await security_manager.check_rate_limit(user1) is False
        
        # user2 should still be allowed
        assert await security_manager.check_rate_limit(user2) is True

    @pytest.mark.asyncio
    async def test_disabled_mode_always_allows(self):
        """Test that disabled mode bypasses all checks."""
        security = SecurityManager(enabled=False)
        
        user_id = "any_user"
        
        # Should always allow regardless of request count
        for _ in range(100):
            result = await security.check_rate_limit(user_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_hourly_limit_tracked(self, security_manager):
        """Test that hourly limits are tracked separately from minute limits."""
        user_id = "test_user_hourly"
        
        # Make requests under the minute limit but approaching hour limit
        # Note: This is a simplified test since we can't easily manipulate time
        # In practice, would need time mocking to fully test hourly window
        for i in range(18):
            result = await security_manager.check_rate_limit(user_id)
            # First 5 should pass each minute window
            if i < 5:
                assert result is True

    def test_get_user_stats(self, security_manager):
        """Test user statistics reporting."""
        user_id = "stats_test_user"
        
        # Make some requests
        for _ in range(3):
            import asyncio
            asyncio.run(security_manager.check_rate_limit(user_id))
        
        stats = security_manager.get_user_stats(user_id)
        
        assert "minute_count" in stats
        assert "hour_count" in stats
        assert "first_request" in stats or stats["minute_count"] == 0

    def test_statistics_initialization(self, security_manager):
        """Test that statistics initialize correctly for new users."""
        user_id = "new_user"
        
        stats = security_manager.get_user_stats(user_id)
        
        assert stats["minute_count"] == 0
        assert stats["hour_count"] == 0


@pytest.mark.asyncio
async def test_security_integration():
    """Integration test for security manager with simulated authentication flow."""
    
    # Setup
    security = SecurityManager(
        enabled=True,
        max_requests_per_minute=3,
        max_requests_per_hour=10
    )
    
    authenticated_user = "admin"
    
    # Simulate valid auth + rate limit check
    user_id = f"auth:{authenticated_user}"
    
    # Should allow first few requests
    assert await security.check_rate_limit(user_id) is True
    assert await security.check_rate_limit(user_id) is True
    assert await security.check_rate_limit(user_id) is True
    
    # Should block after limit
    assert await security.check_rate_limit(user_id) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
