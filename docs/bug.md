# ZTA-AI — Full Codebase Audit & GitHub Copilot Fix Prompt

> Generated from full read of `/backend`, `/frontend`, `/docs`, `docker-compose.yml` and all spec files.
> Verified by running the code in a live container.

---

## PART 1: WHAT'S WRONG (Bug Audit)

---

### 🔴 CRITICAL BUGS (Pipeline-Breaking)

---

#### BUG-01 — Output Guard false-positives block nearly all SLM templates

**File:** `backend/app/slm/output_guard.py`

**What's wrong:**
The `DISALLOWED_OUTPUT_PATTERNS` list contains `\bfrom\b` and `\btable\b` as banned words. These are common English words that appear in almost every natural-language sentence the SLM generates. For example:

- `"Results from your last semester: [SLOT_1]"` → **BLOCKED**
- `"Data from the campus report: [SLOT_1]"` → **BLOCKED**
- `"Your attendance table for this month: [SLOT_1]"` → **BLOCKED**

This means the SLM almost always fails the output guard, the pipeline throws `UnsafeOutputError`, and the user gets an error instead of an answer. This is a **complete pipeline failure for the majority of queries.**

**What it should be:**
The guard should only block SQL injection patterns (full SQL fragments), not isolated common English words. The patterns need to be tightened to require SQL context:

```python
# WRONG - too broad
re.compile(r"\bfrom\b", re.IGNORECASE)

# RIGHT - require SQL context
re.compile(r"\bSELECT\s+.+\s+FROM\b", re.IGNORECASE)
re.compile(r"\bFROM\s+\w+\s+(WHERE|JOIN|LIMIT)\b", re.IGNORECASE)
re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE)
re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE)
```

---

#### BUG-02 — Pipeline stage order: SLM runs BEFORE policy check

**File:** `backend/app/services/pipeline.py`

**What's wrong:**
Looking at the pipeline stage order:
- Stage 3: `slm_render` — calls the external SLM API, generates template
- Stage 6: `policy_authorization` — checks if user is allowed to make this query

This means the system **calls an external SLM API and spends money/latency on every query that will later be rejected by policy.** If a student tries to access finance data, the SLM renders a template for them before the policy engine blocks the request.

**Spec says:** L5 Policy Engine runs before L9 SLM Runtime. The correct order in the spec is:
`Interpreter → Compiler → Policy Engine → Tool Layer → Claim Engine → Context Governance → SLM`

**What the order should be:**
1. Interpreter (Stage 1)
2. Intent cache check (Stage 2)
3. **Policy authorization (Stage 3) — move this up**
4. SLM render on cache miss (Stage 4)
5. Output guard (Stage 5)
6. Tool execution (Stage 6)
7. Field masking (Stage 7)
8. Detokenization (Stage 8)

---

#### BUG-03 — `query_builder.py` imports from `scripts/` (dependency inversion violation)

**File:** `backend/app/compiler/query_builder.py`, line 1:
```python
from scripts.ipeds_import import IPEDS_TENANT_ID
```

**What's wrong:**
The `compiler` is a core backend layer. It should never import from `scripts/` — that directory is for one-off data import scripts, not application code. This creates a hard coupling between the production compiler and a bootstrap script, and will fail in any environment where the scripts directory isn't in the Python path.

**What it should be:**
`IPEDS_TENANT_ID` should be defined in `app/core/config.py` as a settings field:
```python
ipeds_tenant_id: str = Field(default="ipeds-tenant-uuid-here")
```
Or in a constants module at `app/core/constants.py`. The `scripts/` directory should never be imported by application code.

---

### 🟠 SECURITY BUGS

---

#### BUG-04 — CORS wildcard `allow_origins=["*"]` in production config

**File:** `backend/app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ← WRONG
    allow_credentials=True,
    ...
)
```

**What's wrong:**
A zero-trust enterprise system with `allow_credentials=True` cannot use `allow_origins=["*"]`. This combination is rejected by browsers (it's a CORS spec violation) and means any website can make authenticated requests to your API from a victim's browser. For a system handling student PII, grades, and finance data, this is a critical security hole.

**What it should be:**
```python
allowed_origins = settings.allowed_origins  # list from env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    ...
)
```
And add to `config.py`:
```python
allowed_origins: list[str] = Field(default=["http://localhost:8080"])
```

---

#### BUG-05 — JWT default secret key is `"change-me"`

**File:** `backend/app/core/config.py`

```python
jwt_secret_key: str = Field(default="change-me")
```

**What's wrong:**
If someone forgets to set `JWT_SECRET_KEY` in the `.env` file, the system silently uses `"change-me"` as the signing secret. Anyone who knows this default can forge valid JWTs for any user on any tenant. The application must refuse to start if this value is not explicitly set.

**What it should be:**
```python
jwt_secret_key: str = Field(...)  # No default — required field, will raise on startup if missing
```
And add a startup validation check:
```python
@app.on_event("startup")
def on_startup():
    if settings.jwt_secret_key in ("change-me", ""):
        raise RuntimeError("JWT_SECRET_KEY must be set to a secure value before running in any environment")
    create_all_tables()
```

---

#### BUG-06 — `device_trusted=True` and `mfa_verified=True` hardcoded in auth

**File:** `backend/app/identity/service.py`

```python
def authenticate_google(
    self,
    db: Session,
    google_token: str,
    session_ip: str | None = None,
    device_trusted: bool = True,   # ← always trusted
    mfa_verified: bool = True,     # ← always verified
) -> tuple[str, User, ScopeContext]:
```

**What's wrong:**
The ABAC policy engine has rules that block sensitive finance/HR queries unless `device_trusted=True` and `mfa_verified=True`. But both are hardcoded to `True` at login, so **the ABAC device trust and MFA checks are permanently bypassed.** The security controls exist but are never enforced.

**What it should be:**
These should come from the request context — the client should send device fingerprint and the MFA status should come from the Google OAuth token claims. At minimum, `device_trusted` and `mfa_verified` should default to `False` and be explicitly elevated when the conditions are actually verified.

---

#### BUG-07 — IT Head `masked_fields=["*"]` masks everything including admin data

**File:** `backend/app/identity/service.py`

```python
PersonaType.it_head: ["*"],  # mask everything
```

**What's wrong:**
The IT Head is the admin persona. They manage users, data sources, and audit logs. But their `masked_fields` is `["*"]` which means in theory every value they retrieve would be masked as `***MASKED***`. The field masking applies after tool execution — it should only apply to the chat/data query path, not to admin panel responses. Currently the masking logic runs for all values universally.

---

### 🟡 CORRECTNESS BUGS

---

#### BUG-08 — `datetime.utcnow()` deprecated in Python 3.12+

**File:** `backend/app/services/rate_limiter.py`

```python
day_key = datetime.utcnow().strftime("%Y%m%d")
```

**What's wrong:**
`datetime.utcnow()` is deprecated since Python 3.12 and will be removed in a future version. The rest of the codebase correctly uses `datetime.now(tz=UTC)`. This is an inconsistency that will produce deprecation warnings and eventually break.

**What it should be:**
```python
from datetime import UTC, datetime
day_key = datetime.now(tz=UTC).strftime("%Y%m%d")
```

---

#### BUG-09 — `ScopeContext` is mutated after construction in `deps.py`

**File:** `backend/app/api/deps.py`

```python
scope = ScopeContext(session_id=str(payload.get("session_id", "")), ...)
if not scope.session_id:
    scope.session_id = f"sid-{user_id[:8]}"  # ← mutating a Pydantic model
```

**What's wrong:**
Pydantic v2 `BaseModel` instances should be treated as immutable. Direct attribute mutation bypasses validation and creates unpredictable behavior. It also signals that `session_id` doesn't have a well-defined default strategy.

**What it should be:**
Handle the default before construction:
```python
session_id = str(payload.get("session_id") or f"sid-{user_id[:8]}")
scope = ScopeContext(session_id=session_id, ...)
```

---

#### BUG-10 — Chat history is session-scoped, lost between logins

**File:** `backend/app/services/history_service.py`, `backend/app/api/routes/chat.py`

**What's wrong:**
The `history_service` stores messages keyed by `(tenant_id, user_id, session_id)`. The `session_id` is generated fresh via `uuid.uuid4()` on every `authenticate_google()` call. So every time a user logs in, they start with an empty chat history even though their previous queries are in the database.

**What it should be:**
History retrieval should query by `(tenant_id, user_id)` without session_id filter (or with a longer-lived session key stored in the JWT that persists for a configurable period), so users see their recent history across sessions.

---

#### BUG-11 — `domain_gate.py` uses the word "public" as a campus domain trigger

**File:** `backend/app/interpreter/domain_gate.py`

```python
"campus": (..., "public", "private", ...)
```

**What's wrong:**
The word "public" is in the campus domain keyword list. This means:
- `"make this data public"` → detected as campus domain query
- `"public holiday today"` → detected as campus domain query
- `"is this a public API"` → detected as campus domain query

These false positives mean benign queries get routed through the wrong domain pipeline.

**What it should be:**
Use more specific phrases: `"public institution"`, `"public university"`, `"public sector"` instead of the bare word `"public"`.

---

#### BUG-12 — Alembic is in requirements but schema is created via `create_all()`

**File:** `backend/requirements.txt`, `backend/app/db/init_db.py`

**What's wrong:**
`alembic==1.14.1` is listed as a dependency, but the codebase uses `Base.metadata.create_all(bind=engine)` for schema creation, completely bypassing Alembic. There are no migration files anywhere in the repo. This means:

1. Schema changes require dropping and recreating the database
2. The alembic dependency is dead weight
3. In production, you can't evolve the schema without data loss

**What it should be:**
Either remove Alembic and document that `create_all()` is intentional for the current phase, OR initialize Alembic properly with `alembic init alembic`, generate an initial migration, and replace `create_all()` with `alembic upgrade head` in the startup script.

---

#### BUG-13 — CSV files (19MB+) committed directly to the repo

**File:** `backend/ef2024a.csv` (19MB), `backend/hd2024.csv` (3.6MB), etc.

**What's wrong:**
Large CSV data files are committed to Git. This bloats the repo, slows down clones, and is not how production data should be managed. The Dockerfile copies them into the image with `COPY *.csv ./`, making the Docker image unnecessarily large.

**What it should be:**
The IPEDS seed data should be stored in an S3 bucket or similar object storage and downloaded during the `db-init` container's startup. At minimum, add them to `.gitignore` and document where to download them.

---

#### BUG-14 — `db-init` container has no restart policy; if it fails, API never starts

**File:** `docker-compose.yml`

**What's wrong:**
The `api` and `worker` services depend on `db-init` with `condition: service_completed_successfully`. If `db-init` fails (e.g., a Python error during seed), the API container never starts and there's no automatic retry. In development this just means the app is silently broken.

**What it should be:**
Add `restart: on-failure` to `db-init`, or restructure so the API handles a missing/empty DB gracefully and performs seeding itself on first boot with a proper idempotency check.

---

#### BUG-15 — No `.env.example` file; `backend/.env` is required but undocumented

**File:** Root of repo

**What's wrong:**
`docker-compose.yml` references `./backend/.env` via `env_file`, but there is no `.env.example` or documentation of what variables are required. A new developer running `docker compose up --build` will get a silent failure or misconfigured app. The `SLM_API_KEY` in particular is required for the SLM path but not obviously documented.

**What it should be:**
Add a `backend/.env.example` file with all required and optional variables, their expected format, and safe defaults (with a comment warning which ones MUST be changed for security).

---

### 🔵 ARCHITECTURE GAPS (vs. Spec)

---

#### GAP-01 — Context Governance Layer (L8) is missing

**Spec says:** Before the SLM receives data, a Context Governance Layer must minimize, redact, and filter claims — preventing inference attacks and ensuring the SLM only sees the minimum necessary information.

**Current state:** There is no `context_governance/` module. The SLM receives the `InterpretedIntent` object directly which includes the full `raw_prompt`, `sanitized_prompt`, and `aliased_prompt`. The SLM call in `slm/simulator.py` passes `intent.name`, `intent.domain`, `intent.entity_type` etc., which is closer to correct, but the formal governance layer does not exist as an independent, auditable step.

---

#### GAP-02 — SLM is NOT sandboxed — it's just an OpenAI-compatible API call

**Spec says:** The SLM runs in an isolated container with no network access to internal systems, no persistent storage, and no tool calling.

**Current state:** The `SLMSimulator` calls `openai.OpenAI(base_url=settings.slm_base_url, ...)` — this is an API call to an external hosted model (NVIDIA NIM or similar). There is no isolation, no container boundary, no network restriction. The SLM provider (e.g., NVIDIA) receives the full prompt including persona type, intent name, domain, entity type, and slot descriptions. There is no sandbox.

---

#### GAP-03 — Frontend is vanilla HTML/JS, not Next.js as specified

**Spec says:** Frontend: Next.js 14 (App Router) with Tailwind CSS + shadcn/ui. State Management: Zustand.

**Current state:** `frontend/` is a single `index.html` + `script.js` + `style.css` served by nginx. This is a developer testing UI, not the production frontend. The Streamlit frontend (`streamlit_frontend/`) exists as an alternative but also doesn't match the spec.

---

#### GAP-04 — No real Google OAuth — only mock mode

**Spec says:** Sprint 1 includes real Google OAuth / SSO integration.

**Current state:** `config.py` has `use_mock_google_oauth: bool = Field(default=True)`. The real OAuth path in `identity_service.py` raises `AuthenticationError("Real Google OAuth validation is not enabled in this build")`. Real Google OAuth has not been implemented.

---

#### GAP-05 — No Alembic migrations, no Vector DB, no real connectors

- No Alembic migration files exist
- No Pinecone/Weaviate vector DB integration (spec requires it for document search/RAG)
- `ConnectorRegistry` always returns `mock_claims_connector` regardless of source type — ERPNext, Google Sheets, MySQL connectors are not implemented
- `SQLConnector.execute_query()` raises `NotImplementedError`

---

## PART 2: GITHUB COPILOT FIX PROMPT

Copy-paste this entire prompt into GitHub Copilot Chat in your IDE with the full `ztaai` repo open.

---

```
You are an expert Python/FastAPI engineer. I need you to fix a series of bugs in the ZTA-AI codebase (a Zero Trust enterprise AI gateway). Below are the exact bugs, the exact files, and the exact fix required for each. Apply ALL fixes. Do not change anything not listed. After applying fixes, run `python -m pytest` from the `backend/` directory to verify nothing is broken.

The codebase is located in the repo root. Backend is in `backend/`, frontend in `frontend/`.

---

## FIX 1 — output_guard.py: Remove false-positive patterns

FILE: backend/app/slm/output_guard.py

PROBLEM: `DISALLOWED_OUTPUT_PATTERNS` includes `\bfrom\b` and `\btable\b` which match common English words and block almost every SLM-generated template.

CHANGE: Replace the entire `DISALLOWED_OUTPUT_PATTERNS` list with SQL-context-aware patterns:

```python
DISALLOWED_OUTPUT_PATTERNS = [
    re.compile(r"\bSELECT\s+.{0,50}\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bFROM\s+\w+\s+(WHERE|JOIN|LIMIT|GROUP)\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
    re.compile(r"\bCREATE\s+TABLE\b", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"\bschema\s+name\b", re.IGNORECASE),
    re.compile(r"\bcolumn\s+name\b", re.IGNORECASE),
]
```

Also update the `validate()` method: remove the bare `\bschema\b` and `\btable\b` checks that were in the old list. Keep the `contains_raw_number` check, the real identifier check, and the `[SLOT_]` presence check.

---

## FIX 2 — pipeline.py: Move policy_authorization BEFORE slm_render

FILE: backend/app/services/pipeline.py

PROBLEM: Stage 3 is `slm_render` and Stage 6 is `policy_authorization`. Policy must run before the SLM to avoid wasting API calls on blocked queries.

CHANGE: In the `process_query` method, reorder the stages so the pipeline inside the `try` block runs in this order:

1. Stage 1: interpreter (keep as-is)
2. Stage 2: intent_cache check (keep as-is)
3. Stage 3: **policy_authorization** (move from Stage 6 to here, right after cache check)
4. Stage 4: slm_render on cache miss (was Stage 3)
5. Stage 5: output_guard (was Stage 4)
6. Stage 6: compiler / compile_intent (was Stage 5)
7. Stage 7: tool_execution (was Stage 7, keep index)
8. Stage 8: field_masking (keep)
9. Stage 9: detokenization (keep)
10. Stage 10: cache_storage (keep)
11. Stage 11: history_assistant_message (keep)
12. Stage 12: audit_logging (keep)

Update the `stage_index` integers passed to `_track_stage` to match the new order. The policy_authorization call should come before the SLM render block and before compiler.compile_intent — it needs `interpreter_output.intent` and a compiled plan. Since the plan isn't compiled yet at Stage 3, move the policy check to after Stage 6 (compiler) but before Stage 7 (tool execution) if it requires `compiled_query`. The key constraint is: **policy must run before tool execution AND before SLM render.** The cleanest approach:

1. interpreter
2. intent_cache
3. compiler (build the plan early — it's deterministic and cheap)
4. policy_authorization (now has both intent and plan)
5. slm_render (only if policy passed)
6. output_guard
7. tool_execution
8. field_masking
9. detokenization
10. cache_storage
11. history
12. audit

---

## FIX 3 — query_builder.py: Remove import from scripts/

FILE: backend/app/compiler/query_builder.py

PROBLEM: Line 1 imports `from scripts.ipeds_import import IPEDS_TENANT_ID`. Application code must not import from scripts/.

CHANGE:
1. In `backend/app/core/config.py`, add a new field to the `Settings` class:
   ```python
   ipeds_tenant_id: str = Field(default="ipeds-tenant-00000000-0000-0000-0000-000000000001")
   ```
2. In `backend/app/compiler/query_builder.py`, replace:
   ```python
   from scripts.ipeds_import import IPEDS_TENANT_ID
   ```
   with:
   ```python
   from app.core.config import get_settings as _get_settings
   ```
   And replace the usage `scope.tenant_id == IPEDS_TENANT_ID` with:
   ```python
   scope.tenant_id == _get_settings().ipeds_tenant_id
   ```

---

## FIX 4 — main.py: Fix CORS wildcard

FILE: backend/app/main.py

PROBLEM: `allow_origins=["*"]` with `allow_credentials=True` is a CORS security violation and browsers reject it.

CHANGE:
1. Add to `Settings` class in `backend/app/core/config.py`:
   ```python
   allowed_origins: list[str] = Field(default=["http://localhost:8080", "http://localhost:3000"])
   ```
2. In `backend/app/main.py`, replace:
   ```python
   allow_origins=["*"],
   ```
   with:
   ```python
   allow_origins=settings.allowed_origins,
   ```

---

## FIX 5 — config.py: Make JWT secret required, add startup validation

FILE: backend/app/core/config.py and backend/app/main.py

PROBLEM: `jwt_secret_key` defaults to `"change-me"`. If not set, the system silently uses an insecure key.

CHANGE:
1. In `Settings`, change:
   ```python
   jwt_secret_key: str = Field(default="change-me")
   ```
   to:
   ```python
   jwt_secret_key: str = Field(default="change-me")  # keep default for dev
   ```
   But add a startup check in `backend/app/main.py` inside `on_startup()`:
   ```python
   @app.on_event("startup")
   def on_startup() -> None:
       if settings.environment == "production" and settings.jwt_secret_key == "change-me":
           raise RuntimeError(
               "JWT_SECRET_KEY must be set to a secure random value in production. "
               "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
           )
       create_all_tables()
   ```

---

## FIX 6 — rate_limiter.py: Replace deprecated datetime.utcnow()

FILE: backend/app/services/rate_limiter.py

PROBLEM: `datetime.utcnow()` is deprecated in Python 3.12+.

CHANGE: Replace:
```python
from datetime import datetime
...
day_key = datetime.utcnow().strftime("%Y%m%d")
```
with:
```python
from datetime import UTC, datetime
...
day_key = datetime.now(tz=UTC).strftime("%Y%m%d")
```

---

## FIX 7 — deps.py: Stop mutating ScopeContext after construction

FILE: backend/app/api/deps.py

PROBLEM: `scope.session_id = f"sid-{user_id[:8]}"` mutates a Pydantic model after construction.

CHANGE: Replace the two-step pattern:
```python
scope = ScopeContext(session_id=str(payload.get("session_id", "")), ...)
if not scope.session_id:
    scope.session_id = f"sid-{user_id[:8]}"
```
with a single construction:
```python
_session_id = str(payload.get("session_id") or f"sid-{user_id[:8]}")
scope = ScopeContext(session_id=_session_id, ...)
```
Remove the `if not scope.session_id:` block entirely.

---

## FIX 8 — domain_gate.py: Fix over-broad "public" and "private" keywords

FILE: backend/app/interpreter/domain_gate.py

PROBLEM: `"public"` and `"private"` are bare keywords for the campus domain, causing false positives like "public holiday" or "private message" triggering campus domain detection.

CHANGE: In `DOMAIN_KEYWORDS["campus"]`, replace `"public"` and `"private"` with more specific phrases:
```python
"campus": (
    "cross campus",
    "campus aggregate",
    "enrollment",
    "enrolment",
    "enrolled",
    "headcount",
    "institution",
    "hbcu",
    "sector",
    "public institution",
    "public university",
    "public college",
    "private institution",
    "private university",
    "private college",
    "demographics",
    "size distribution",
    "students",
),
```

---

## FIX 9 — Create backend/.env.example

FILE: Create new file `backend/.env.example`

Create this file with all required and optional environment variables:

```bash
# =============================================================================
# ZTA-AI Backend — Environment Variables
# Copy this file to .env and fill in the values before running.
# =============================================================================

# Application
APP_NAME=ZTA-AI
ENVIRONMENT=development   # development | production

# Database (required)
DATABASE_URL=postgresql+psycopg2://zta:zta@localhost:5432/zta_ai

# Redis (required)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security (CHANGE THESE IN PRODUCTION)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
JWT_EXP_MINUTES=30
JWT_REFRESH_WINDOW_MINUTES=5

# CORS (comma-separated list of allowed frontend origins)
ALLOWED_ORIGINS=["http://localhost:8080","http://localhost:3000"]

# Auth
USE_MOCK_GOOGLE_OAUTH=true
MOCK_GOOGLE_TOKEN_PREFIX=mock:

# SLM (required for real SLM mode; leave blank to disable SLM)
SLM_PROVIDER=simulator
SLM_BASE_URL=https://integrate.api.nvidia.com/v1
SLM_API_KEY=                     # REQUIRED for hosted SLM — get from NVIDIA/Azure
SLM_MODEL=microsoft/phi-3-mini-128k-instruct
SLM_TEMPERATURE=0.2
SLM_TOP_P=0.7
SLM_MAX_TOKENS=256

# Limits
DAILY_QUERY_LIMIT=50
INTENT_CACHE_TTL_SECONDS=86400

# IPEDS tenant (the built-in demo tenant seeded from IPEDS CSV data)
IPEDS_TENANT_ID=ipeds-tenant-00000000-0000-0000-0000-000000000001
```

---

## FIX 10 — Add .gitignore entries for CSV data files

FILE: backend/.gitignore (or root .gitignore)

PROBLEM: Large IPEDS CSV files (19MB+) are committed to the repo.

CHANGE: Add these entries to the `.gitignore` at the repo root:
```
# Large data files — download separately per IPEDS import instructions
backend/*.csv
backend/*.CSV
```

Note: After adding to .gitignore, run `git rm --cached backend/*.csv` to untrack the files without deleting them locally. Document in `backend/README.md` how to download the IPEDS data files.

---

## AFTER ALL FIXES — Verify

Run the following from `backend/`:
```bash
python -m pytest tests/ -v
```

And manually verify:
1. `python -c "from app.slm.output_guard import output_guard; output_guard.validate('Results from your last semester: [SLOT_1]', []); print('OK')"` — should print OK, not raise
2. `python -c "from app.compiler.query_builder import query_builder; print('OK')"` — should not import from scripts
3. `python -c "from app.core.config import get_settings; s = get_settings(); print(s.allowed_origins)"` — should print list, not wildcard
4. `python -c "from app.services.rate_limiter import rate_limiter_service; import inspect; src = inspect.getsource(type(rate_limiter_service).check_and_increment); print('utcnow' not in src)"` — should print True
```

---

## PART 3: WHAT THE RIGHT APPROACH IS (Architecture Summary)

The code is well-structured and the core idea is sound. Here's what you're doing right vs. what needs to change:

| Area | Current State | Correct Approach |
|---|---|---|
| Pipeline security | SLM runs before policy | Policy → Compiler → SLM → Tools |
| Output guard | Blocks common English words | Blocks SQL fragments only |
| CORS | Wildcard `*` | Explicit origin whitelist from env |
| JWT secret | Hardcoded default | Required env var, fail-fast on startup |
| MFA/device trust | Always `True` | Must come from real OAuth claims |
| Schema coupling | `compiler` imports `scripts/` | Constants in `core/config.py` |
| Alembic | Installed but unused | Either use it or remove it |
| Migrations | `create_all()` | Alembic migrations for production |
| Frontend | Raw HTML/JS | Next.js 14 + Tailwind + shadcn/ui per spec |
| Data files | 19MB CSV in git | Object storage (S3), downloaded at seed time |
| SLM isolation | External API call | Containerized, network-isolated inference |
| Context Governance | Missing entirely | Add `app/context_governance/` layer before SLM |