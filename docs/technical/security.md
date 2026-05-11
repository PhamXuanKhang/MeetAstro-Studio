# Security

Security considerations and implementation details for AI Meeting Assistant.

---

## Overview

AI Meeting Assistant handles sensitive data:
- Meeting audio recordings (potentially confidential conversations)
- Transcript text (confidential content)
- Provider credentials (API keys, tokens)
- Jira integration credentials

This document outlines the security measures implemented.

---

## Credential Management

### Supabase Keys

| Key | Used by | Purpose |
|-----|---------|---------|
| `SUPABASE_URL` | Backend + Electron | Supabase project URL |
| `SUPABASE_ANON_KEY` | Electron frontend only | Public, for client-side auth |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only | Full database access, never expose |

**Important:** Never put `SUPABASE_SERVICE_ROLE_KEY` in frontend code or Electron `.env`.

### Credential Vault (Fernet Encryption)

Provider credentials (OpenAI API keys, Jira tokens, etc.) are encrypted at rest using **Fernet symmetric encryption** before storing in PostgreSQL.

**Implementation:** `src/modules/credential_vault.py`

```python
from cryptography.fernet import Fernet

def encrypt(plaintext: str) -> str:
    """Encrypt plaintext using APP_SECRET_KEY."""
    key = settings.APP_SECRET_KEY.encode()
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    """Decrypt ciphertext using APP_SECRET_KEY."""
    key = settings.APP_SECRET_KEY.encode()
    f = Fernet(key)
    return f.decrypt(ciphertext.encode()).decode()
```

### Key Management

- **APP_SECRET_KEY**: 32-byte base64-encoded Fernet key
- Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Store in `.env` file (never commit to git)
- **Required** for credential vault operations

### Encrypted Fields

| Table | Column | Encryption |
|-------|--------|------------|
| `provider_configs` | `config_json` | Fernet |

---

## Environment Variables

### Sensitive Variables (Never Commit)

| Variable | Description | Risk if Leaked |
|----------|-------------|----------------|
| `OPENAI_API_KEY` | OpenAI API access | Unauthorized API usage, cost |
| `APP_SECRET_KEY` | Fernet encryption key | Credential decryption |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase database access | Full data access |
| `JIRA_API_TOKEN` | Jira API token | Unauthorized Jira access |

### .gitignore Protection

The following are in `.gitignore`:
```
.env
*.pem
*.key
data/recordings/
```

### .env.example

A sanitized template is provided:
```bash
OPENAI_API_KEY=your_openai_api_key_here
APP_SECRET_KEY=your_fernet_key_here
# ... other variables with placeholder values
```

---

## API Security

### Current Implementation

| Measure | Status | Notes |
|---------|--------|-------|
| HTTPS | Deployment-dependent | Use nginx/reverse proxy |
| Authentication | Supabase Auth | Email/password + OAuth |
| Rate Limiting | Basic | Per-IP limiting available |
| CORS | Configured | For Flet/Electron desktop clients |
| Input Validation | Pydantic | All API inputs validated |

### Rate Limiting

Basic rate limiting is available via `src/api/rate_limit.py`:

```python
from fastapi import Request
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/meetings")
@limiter.limit("30/minute")
async def list_meetings(request: Request):
    ...
```

### Input Validation

All API endpoints use **Pydantic schemas** for request validation:
- `src/api/schemas/meeting_schemas.py`
- `src/api/schemas/review_schemas.py`
- `src/api/schemas/task_schemas.py`

Example:
```python
class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(default="default_user", max_length=100)
```

---

## Data Protection

### Audio Files

- Stored locally on server: `data/recordings/`
- Not accessible via API (no static file serving)
- Consider: disk encryption, retention policies

### Database

- PostgreSQL with asyncpg
- Connection via environment variable (not hardcoded)
- Credentials stored encrypted in `provider_configs`

### Transcript & Analysis

- Stored in PostgreSQL (not encrypted at rest by default)
- Consider: PostgreSQL TDE (Transparent Data Encryption) for production

---

## External API Security

### OpenAI API

- API key passed via `Authorization: Bearer` header
- HTTPS only
- No sensitive data stored on OpenAI side (API calls are stateless)

### Jira API

- Basic Auth: `JIRA_EMAIL` + `JIRA_API_TOKEN`
- HTTPS only
- Stub mode when credentials missing (no real API calls)

```python
# JiraClient auto-detects missing credentials
if not all([base_url, email, token, project_key]):
    self._is_stub = True  # No API calls, returns fake keys
```

---

## Potential Vulnerabilities & Mitigations

### 1. Command Injection

**Risk:** Audio file paths could be manipulated.

**Mitigation:**
- File paths are server-generated UUIDs
- No user-provided paths executed directly
- `subprocess` calls use list arguments (not shell=True)

### 2. SQL Injection

**Risk:** Database queries with user input.

**Mitigation:**
- SQLAlchemy ORM (parameterized queries)
- No raw SQL with string interpolation
- Pydantic validation on all inputs

### 3. Path Traversal

**Risk:** File access outside intended directories.

**Mitigation:**
- Audio paths are UUID-based
- Server-side path generation
- No user-controlled file paths

### 4. API Key Exposure

**Risk:** Keys logged or exposed in errors.

**Mitigation:**
- Keys from environment variables only
- Error messages don't include credentials
- Logging excludes sensitive fields

### 5. Credential Vault Key Loss

**Risk:** Losing `APP_SECRET_KEY` makes encrypted credentials unrecoverable.

**Mitigation:**
- Document key backup procedures
- Consider key rotation strategy

---

## Security Checklist (Deployment)

### Before Production

- [ ] Generate unique `APP_SECRET_KEY`
- [ ] Configure Supabase project with proper RLS policies
- [ ] Set `SUPABASE_SERVICE_ROLE_KEY` only in backend environment
- [ ] Set `SUPABASE_ANON_KEY` in Electron frontend `.env`
- [ ] Configure HTTPS (nginx/reverse proxy)
- [ ] Set appropriate file permissions (`chmod 600 .env`)
- [ ] Disable debug logging in production
- [ ] Configure firewall (only expose port 443)

### Ongoing

- [ ] Rotate API keys periodically
- [ ] Monitor for unusual API usage
- [ ] Review logs for security events
- [ ] Update dependencies (security patches)

---

## Future Enhancements

| Feature | Priority | Notes |
|---------|----------|-------|
| User authentication | High | OAuth2 / JWT |
| Role-based access | Medium | Admin, user roles |
| Audit logging | Medium | Track who did what |
| Data retention policies | Medium | Auto-delete old recordings |
| API key rotation | Low | Scheduled key updates |
| End-to-end encryption | Low | Client-side encryption |
