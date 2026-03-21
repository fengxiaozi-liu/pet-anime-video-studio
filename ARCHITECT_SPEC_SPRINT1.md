# API Security & Authentication - Sprint 1 Specification

**Project:** Pet Anime Video Backend  
**Sprint:** Sprint 1 - API Security & Authentication  
**Status:** Priority 1 (Production Blocker)  
**Created:** 2026-03-21  
**Target Delivery:** 2026-03-24 (3 days from now)  

---

## Executive Summary

The pet-anime-video project is currently **4 days overdue** from its target delivery date (2026-03-17). This sprint focuses on implementing a production-ready API authentication system that adds **Bearer Token authentication via `X-API-Key` header** while maintaining backward compatibility with existing HTTP Basic Auth.

### Key Objectives

1. ✅ Add API Token authentication via `X-API-Key` header
2. ✅ Maintain backward compatibility with HTTP Basic Auth
3. ✅ Zero breaking changes to existing functionality
4. ✅ Minimal performance overhead (<5ms per request)
5. ✅ Clear, actionable error messages for unauthorized access

---

## Table of Contents

1. [Overview](#overview)
2. [Current Architecture](#current-architecture)
3. [Threat Model](#threat-model)
4. [Design Specification](#design-specification)
5. [Implementation Details](#implementation-details)
6. [Modified Files List](#modified-files-list)
7. [Testing Strategy](#testing-strategy)
8. [Rollback Plan](#rollback-plan)
9. [Deployment Checklist](#deployment-checklist)

---

## Overview

### What We're Building

A dual-authentication system supporting:
- **Primary:** API Token via `X-API-Key` header (recommended for APIs/scripts)
- **Secondary:** HTTP Basic Auth (maintained for UI compatibility)

Both methods share the same rate limiting and authorization logic.

### Why X-API-Key?

| Header Type | Use Case | Pros | Cons |
|-------------|----------|------|------|
| `X-API-Key` | Programmatic access | Simple, no encoding, easy to debug | Must use custom header |
| `Authorization: Basic` | Browser/UI access | Standard, widely supported | Base64 encoding, browser prompts |

We implement both to support:
- External API consumers (X-API-Key)
- Web UI users (HTTP Basic Auth)

---

## Current Architecture

### Existing Security Implementation

Located in `/backend/app/security.py`:

```python
class SecurityManager:
    """Rate limiting and basic auth management."""
    
    def __init__(self, enabled=True, max_requests_per_minute=10, ...):
        self.enabled = enabled
        self.rate_limiter = Limiter(...)
```

Current flow:
1. All `/api/*` endpoints require `authenticated_endpoint` dependency
2. `authenticated_endpoint` calls `verify_api_credentials` (HTTP Basic)
3. Rate limiting applied per authenticated user
4. Global `security_manager` instance manages state

### Current Protected Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/jobs` | GET | List recent jobs |
| `/api/jobs` | POST | Create new job |
| `/api/jobs/{id}` | GET | Get job details |
| `/api/jobs/{id}/result` | GET | Download video result |
| `/api/assets` | GET | List assets |
| `/api/assets` | POST | Upload asset |
| `/api/assets/{id}` | GET | Download asset |
| `/api/platform-templates` | GET | List templates |

### Public Endpoints (No Auth Required)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Web UI homepage |
| `/health` | GET | Health check |
| `/static/*` | GET | Static files |

---

## Threat Model

### Assets to Protect

1. **API Access:** Prevent unauthorized job submission
2. **User Data:** Protect uploaded images and generated videos
3. **Compute Resources:** Limit DoS via rate limiting
4. **AI Provider Keys:** Keep cloud provider credentials secret

### Attack Vectors

| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Brute force credential guessing | Medium | High | Rate limiting, strong password policy |
| Token leakage in logs | Medium | High | Never log full tokens |
| Replay attacks | Low | Medium | Tokens are stateless; rotate periodically |
| DoS via API abuse | High | Medium | Rate limiting per IP/user |
| Unauthorized data access | Medium | High | Auth required on all `/api/*` endpoints |

### Out of Scope (Future Sprints)

- OAuth 2.0 / OIDC integration
- Multi-tenancy support
- Token expiration/rotation automation
- Audit logging
- IP whitelisting

---

## Design Specification

### Token Format

```
Format: pav-{uuid4}-{hash_suffix}
Example: pav-a1b2c3d4-e5f6-7890-abcd-ef1234567890-9k2mPq

Components:
- Prefix: "pav-" (Pet Anime Video identifier)
- UUID: Random UUID4 for uniqueness
- Hash suffix: First 6 chars of SHA256(token_salt + uuid) for validation
```

### Storage Mechanism

Tokens are configured via `.env` file (no database):

```env
# API Token Authentication
API_TOKEN=pav-<your-generated-token-here>
API_TOKEN_SECRET=pav-<backup-token-for-rotation>
```

**Why .env?**
- Simple deployment (no DB migration needed)
- Easy rotation (update env var, restart service)
- Works with Docker/Kubernetes secrets
- Fits current architecture pattern

### Authentication Flow

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  verify_api_token_or_basic()       │
│  ┌─────────────────────────────┐   │
│  │ 1. Check X-API-Key header   │   │
│  │    └─ Valid? → Authenticate  │   │
│  └─────────────────────────────┘   │
│           │                         │
│           ▼ No token                │
│  ┌─────────────────────────────┐   │
│  │ 2. Check Authorization      │   │
│  │    (HTTP Basic)             │   │
│  │    └─ Valid? → Authenticate  │   │
│  └─────────────────────────────┘   │
│           │                         │
│           ▼ Both fail               │
│  ┌─────────────────────────────┐   │
│  │ Raise HTTP 401              │   │
│  └─────────────────────────────┘   │
└────────────────┬──────────────────┘
                 │
                 ▼
          ┌──────────────┐
          │ Rate Limit   │
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │  Authorized  │
          └──────────────┘
```

### Error Responses

| Status Code | Scenario | Response Body |
|-------------|----------|---------------|
| `401` | Missing or invalid token | `{"detail": "Missing or invalid API token"}` |
| `401` | Invalid basic auth | `{"detail": "Invalid credentials"}` |
| `403` | Token valid but forbidden | `{"detail": "Access forbidden"}` |
| `429` | Rate limit exceeded | `{"detail": "Rate limit exceeded. Try again later."}` |

---

## Implementation Details

### Step 1: Update Configuration (`config.py`)

**File:** `/backend/app/config.py`

Add token-related settings:

```python
@dataclass
class Settings:
    # Existing fields...
    
    # API Token Authentication
    api_token: str = field(init=False)
    api_token_secret: str = field(default="", init=False)
    
    def __post_init__(self):
        # Existing post-init logic...
        
        # API Token configuration
        self.api_token = os.getenv("API_TOKEN", "")
        self.api_token_secret = os.getenv("API_TOKEN_SECRET", "")
        
        if self.api_token:
            logger.info("API Token authentication enabled")
        else:
            logger.warning("API_TOKEN not configured; only HTTP Basic Auth available")
```

### Step 2: Enhance Security Manager (`security.py`)

**File:** `/backend/app/security.py`

Add token validation method:

```python
import hashlib
import re
import secrets
from typing import Optional

class SecurityManager:
    """Rate limiting and authentication management."""
    
    # Token format regex: pav-{uuid}-{6char_hash}
    TOKEN_PATTERN = re.compile(r'^pav-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}-[a-zA-Z0-9]{6}$')
    
    def __init__(
        self,
        enabled: bool = True,
        max_requests_per_minute: int = 10,
        max_requests_per_hour: int = 100,
        api_token: str = "",
        api_token_secret: str = ""
    ):
        self.enabled = enabled
        self.api_token = api_token
        self.api_token_secret = api_token_secret
        self.rate_limiter = Limiter(
            max_requests=max_requests_per_minute,
            period=60,
        )
        self.hourly_limiter = Limiter(
            max_requests=max_requests_per_hour,
            period=3600,
        )
    
    def validate_api_token(self, token: Optional[str]) -> bool:
        """
        Validate API token from X-API-Key header.
        
        Args:
            token: Token string from request header
            
        Returns:
            True if token is valid, False otherwise
        """
        if not token:
            return False
        
        # Check primary token
        if self._secure_compare(token, self.api_token):
            return True
        
        # Check backup/secret token (for rotation)
        if self.api_token_secret and self._secure_compare(token, self.api_token_secret):
            logger.warning("Backup API token used - consider rotating")
            return True
        
        return False
    
    def _secure_compare(self, val1: str, val2: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        return secrets.compare_digest(val1.encode(), val2.encode())
```

### Step 3: Update Main Application (`main.py`)

**File:** `/backend/app/main.py`

Replace the authentication dependency:

```python
from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials, SecurityScopes

async def verify_api_token_or_basic(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    credentials: Optional[HTTPBasicCredentials] = Security(security, optional=True)
) -> str:
    """
    Verify authentication via API token or HTTP Basic Auth.
    
    Tries API token first, then falls back to HTTP Basic.
    Returns authenticated user identifier for rate limiting.
    
    Raises:
        HTTPException: 401 if neither auth method succeeds
    """
    # Early exit if security disabled
    if security_manager is None or not security_manager.enabled:
        return "unauthenticated"
    
    # Method 1: API Token (X-API-Key header)
    if x_api_key:
        if security_manager.validate_api_token(x_api_key):
            logger.debug("API token authentication successful")
            return "api:token"
        else:
            logger.warning(f"Invalid API token provided")
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid API token",
                headers={"WWW-Authenticate": "APIKey"},
            )
    
    # Method 2: HTTP Basic Auth
    if credentials:
        api_username = os.getenv("API_KEY_USERNAME", "admin")
        api_password = os.getenv("API_KEY_PASSWORD", "changeme123")
        
        if (credentials.username == api_username and 
            security_manager._secure_compare(credentials.password, api_password)):
            logger.debug("HTTP Basic authentication successful")
            return f"basic:{credentials.username}"
    
    # Both methods failed
    logger.warning(f"Authentication failed for request")
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide X-API-Key header or HTTP Basic credentials.",
        headers={
            "WWW-Authenticate": 'Basic realm="Pet Anime Video API", APIKey'
        },
    )


async def authenticated_endpoint(
    user: str = Depends(verify_api_token_or_basic)
) -> str:
    """Dependency for authenticated endpoints with rate limiting."""
    if security_manager and security_manager.enabled:
        if not await security_manager.check_rate_limit(user):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later."
            )
    return user
```

### Step 4: Update Lifespan Initialization

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global security_manager
    settings = get_settings()
    
    logger.info("=== Starting Pet Anime Video Backend ===")
    
    # Initialize security manager with both auth methods
    security_enabled = os.getenv("SECURITY_ENABLED", "true").lower() == "true"
    
    if security_enabled:
        security_manager = SecurityManager(
            enabled=True,
            max_requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
            max_requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "100")),
            api_token=settings.api_token,
            api_token_secret=settings.api_token_secret,
        )
        
        auth_methods = []
        if settings.api_token:
            auth_methods.append("API Token")
        auth_methods.append("HTTP Basic")
        
        logger.info(f"Security enabled with: {', '.join(auth_methods)}")
        logger.info(f"Rate limiting: {security_manager.rate_limiter.max_requests} req/min, {security_manager.hourly_limiter.max_requests} req/hour")
    else:
        security_manager = SecurityManager(enabled=False)
        logger.warning("Security DISABLED - not recommended for production")
    
    yield
    
    # Cleanup if needed
```

### Step 5: Update .env.example

**File:** `/backend/.env.example`

```env
# ===========================================
# API SECURITY (PRODUCTION REQUIRED)
# ===========================================

# Enable/disable entire security layer
SECURITY_ENABLED=true

# --- Method 1: API Token Authentication (Recommended for APIs) ---
# Generate a secure token: python -c "import secrets,uuid; print(f'pav-{uuid.uuid4().hex[:32]}-{secrets.token_urlsafe(8)[:6]}')"
API_TOKEN=pav-your-generated-token-here
API_TOKEN_SECRET=pav-backup-token-for-rotation

# --- Method 2: HTTP Basic Auth (For UI/Browser) ---
API_KEY_USERNAME=admin
API_KEY_PASSWORD=changeme123

# --- Rate Limiting ---
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
```

---

## Modified Files List

| File | Changes | Lines Changed | Risk Level |
|------|---------|---------------|------------|
| `backend/app/config.py` | Add API token fields to Settings | ~10 | Low |
| `backend/app/security.py` | Add token validation methods | ~30 | Medium |
| `backend/app/main.py` | Update auth dependency | ~40 | Medium |
| `backend/.env.example` | Add token config docs | ~15 | Low |
| `backend/Dockerfile` | No changes needed | 0 | None |
| `docker-compose.yml` | No changes needed | 0 | None |

**Total Lines Changed:** ~95 lines across 4 files  
**Estimated Implementation Time:** 2-4 hours

---

## Testing Strategy

### Unit Tests

Create `/backend/tests/test_security.py`:

```python
import pytest
from fastapi import HTTPException
from app.security import SecurityManager
from app.main import verify_api_token_or_basic


class TestSecurityManager:
    
    def test_validate_valid_token(self):
        manager = SecurityManager(enabled=True, api_token="pav-test-token-abc123")
        assert manager.validate_api_token("pav-test-token-abc123") is True
    
    def test_validate_invalid_token(self):
        manager = SecurityManager(enabled=True, api_token="pav-valid-token-xyz789")
        assert manager.validate_api_token("pav-wrong-token-abc123") is False
    
    def test_validate_backup_token(self):
        manager = SecurityManager(
            enabled=True,
            api_token="pav-primary-x",
            api_token_secret="pav-backup-y"
        )
        assert manager.validate_api_token("pav-backup-y") is True
    
    def test_disabled_security(self):
        manager = SecurityManager(enabled=False)
        assert manager.validate_api_token("any-token") is False


class TestVerifyApiTokenOrBasic:
    
    @pytest.mark.asyncio
    async def test_valid_api_token(self):
        # Setup security_manager with test token
        result = await verify_api_token_or_basic(x_api_key="pav-test-valid")
        assert result == "api:token"
    
    @pytest.mark.asyncio
    async def test_valid_basic_auth(self):
        credentials = HTTPBasicCredentials(username="admin", password="testpass")
        result = await verify_api_token_or_basic(credentials=credentials)
        assert result.startswith("basic:")
    
    @pytest.mark.asyncio
    async def test_invalid_both_methods(self):
        with pytest.raises(HTTPException) as exc:
            await verify_api_token_or_basic(
                x_api_key="invalid",
                credentials=HTTPBasicCredentials(username="wrong", password="wrong")
            )
        assert exc.value.status_code == 401
```

### Integration Tests

Create `/backend/tests/test_api_auth.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client with security enabled."""
    os.environ["SECURITY_ENABLED"] = "true"
    os.environ["API_TOKEN"] = "pav-test-token-123456"
    os.environ["API_KEY_USERNAME"] = "testuser"
    os.environ["API_KEY_PASSWORD"] = "testpass"
    
    # Reinitialize security manager for testing
    from app import main
    main.security_manager = main.SecurityManager(
        enabled=True,
        api_token="pav-test-token-123456",
    )
    
    return TestClient(app)


class TestEndpointAuth:
    
    def test_health_no_auth(self, client):
        """Health endpoint should be public."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_api_requires_auth(self, client):
        """API endpoints require authentication."""
        response = client.get("/api/jobs")
        assert response.status_code == 401
    
    def test_api_with_valid_token(self, client):
        """API accepts valid API token."""
        response = client.get(
            "/api/jobs",
            headers={"X-API-Key": "pav-test-token-123456"}
        )
        assert response.status_code == 00
    
    def test_api_with_valid_basic(self, client):
        """API accepts valid HTTP Basic credentials."""
        response = client.get("/api/jobs", auth=("testuser", "testpass"))
        assert response.status_code == 200
    
    def test_api_with_invalid_token(self, client):
        """API rejects invalid token."""
        response = client.get(
            "/api/jobs",
            headers={"X-API-Key": "pav-invalid-token"}
        )
        assert response.status_code == 401
        assert "invalid API token" in response.json()["detail"].lower()
```

### Manual Testing Checklist

Before deployment, manually test:

- [ ] `curl http://localhost:8000/health` returns 200 (no auth needed)
- [ ] `curl http://localhost:8000/api/jobs` returns 401 (auth required)
- [ ] `curl -H "X-API-Key: pav-valid-token" http://localhost:8000/api/jobs` returns 200
- [ ] `curl -u admin:password http://localhost:8000/api/jobs` returns 200
- [ ] Web UI still works with HTTP Basic prompt
- [ ] Rate limiting triggers after N requests
- [ ] Error messages are clear and actionable

---

## Rollback Plan

### If Something Goes Wrong

#### Scenario 1: Auth breaks all API access

**Symptom:** All `/api/*` requests return 401

**Immediate Fix:**
```bash
# Disable security temporarily
export SECURITY_ENABLED=false
docker-compose restart backend
```

**Permanent Fix:** Debug token comparison logic, check env vars are loaded correctly

#### Scenario 2: Memory/performance issues

**Symptom:** Slow response times, high memory usage

**Immediate Fix:**
```bash
# Reduce rate limiter complexity
export RATE_LIMIT_PER_MINUTE=100
export RATE_LIMIT_PER_HOUR=1000
docker-compose restart backend
```

#### Scenario 3: Web UI broken

**Symptom:** HTTP Basic auth prompt doesn't work

**Rollback:** Revert `main.py` changes, deploy previous version:
```bash
git checkout <last-good-commit> backend/app/main.py
docker-compose rebuild backend
docker-compose up -d
```

### Backup Strategy

Before deploying:

```bash
# 1. Tag current working version
git tag -a v0.1-security-rollback <<date>>
git push origin v0.1-security-rollback

# 2. Export current docker image
docker tag pet-anime-backend:latest pet-anime-backend:rollback-$(date +%Y%m%d)
docker push pet-anime-backend:rollback-<<date>>

# 3. Save current .env
cp backend/.env backend/.env.backup-$(date +%Y%m%d)
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Code review completed
- [ ] Unit tests passing (`pytest backend/tests/test_security.py`)
- [ ] Integration tests passing (`pytest backend/tests/test_api_auth.py`)
- [ ] Manual testing checklist complete
- [ ] Backup strategy executed

### Deployment Steps

1. **Generate Production Tokens:**
   ```bash
   # Primary token
   python3 -c "import secrets,uuid; print(f'API_TOKEN=pav-{uuid.uuid4().hex[:32]}-{secrets.token_urlsafe(8)[:6]}')"
   
   # Backup token (for rotation)
   python3 -c "import secrets,uuid; print(f'API_TOKEN_SECRET=pav-{uuid.uuid4().hex[:32]}-{secrets.token_urlsafe(8)[:6]}')"
   ```

2. **Update Environment:**
   ```bash
   cd backend
   cp .env.example .env
   nano .env  # Fill in tokens and credentials
   ```

3. **Deploy:**
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

4. **Verify:**
   ```bash
   # Check logs
   docker-compose logs -f backend
   
   # Test health endpoint
   curl http://localhost:8000/health
   
   # Test API with token
   curl -H "X-API-Key: $API_TOKEN" http://localhost:8000/api/jobs
   ```

### Post-Deployment Monitoring

Monitor for first 24 hours:

- [ ] Error rate in logs (look for 401 spikes)
- [ ] Response time (<200ms for auth'd requests)
- [ ] Memory usage stable
- [ ] Rate limiting working as expected
- [ ] Both auth methods functional

---

## Success Criteria

This sprint is considered complete when:

1. ✅ API Token authentication via `X-API-Key` header works
2. ✅ HTTP Basic Auth still works (backward compatible)
3. ✅ All tests passing (unit + integration)
4. ✅ Zero breaking changes to existing API contracts
5. ✅ Performance impact <5ms per authenticated request
6. ✅ Clear error messages for all auth failures
7. ✅ Documentation updated (this spec + README)

---

## Appendix A: Token Generation Script

Save as `/scripts/generate_token.py`:

```python
#!/usr/bin/env python3
"""Generate secure API tokens for Pet Anime Video."""

import secrets
import uuid
import argparse


def generate_token(prefix: str = "pav") -> str:
    """Generate a secure API token."""
    uid = uuid.uuid4()
    suffix = secrets.token_urlsafe(8)[:6]
    return f"{prefix}-{uid.hex[:8]}-{uid.hex[8:12]}-{uid.hex[12:16]}-{uid.hex[16:20]}-{uid.hex[20:32]}-{suffix}"


def main():
    parser = argparse.ArgumentParser(description="Generate API tokens")
    parser.add_argument("--count", type=int, default=1, help="Number of tokens to generate")
    parser.add_argument("--format", choices=["env", "plain"], default="env",
                       help="Output format")
    args = parser.parse_args()
    
    for i in range(args.count):
        token = generate_token()
        if args.format == "env":
            var_name = "API_TOKEN" if i == 0 else "API_TOKEN_SECRET"
            print(f"{var_name}={token}")
        else:
            print(token)


if __name__ == "__main__":
    main()
```

Usage:
```bash
# Generate primary token
python scripts/generate_token.py --format env

# Generate multiple tokens
python scripts/generate_token.py --count 2 --format env
```

---

## Appendix B: Example cURL Commands

```bash
# Health check (no auth)
curl http://localhost:8000/health

# List jobs with API token
curl -H "X-API-Key: pav-your-token" http://localhost:8000/api/jobs

# List jobs with HTTP Basic
curl -u admin:password http://localhost:8000/api/jobs

# Create job with API token
curl -X POST http://localhost:8000/api/jobs \
  -H "X-API-Key: pav-your-token" \
  -F "prompt=A cute cat playing" \
  -F "images=@cat1.jpg" \
  -F "backend=local"

# Download result
curl -L -o output.mp4 \
  -H "X-API-Key: pav-your-token" \
  http://localhost:8000/api/jobs/{job_id}/result
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-21 | Architect Agent | Initial specification |

---

**END OF SPECIFICATION**

Next Steps:
1. Developer reviews this spec
2. Implement changes (estimated 2-4 hours)
3. Run tests
4. Deploy to staging
5. Manual verification
6. Deploy to production
7. Monitor for 24 hours

**Questions?** Contact the development team immediately - we're on a tight deadline!
