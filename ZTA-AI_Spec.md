# ZTA-AI Campus Platform — Engineering Specification
**Version 1.0 • March 2026 • CONFIDENTIAL — INTERNAL USE ONLY**

---

## 1. What We Are Building
ZTA-AI Campus is a secure, AI-powered internal assistant for universities. It allows every person affiliated with a campus (approx. 20,000 users) to ask natural language questions about university data and receive accurate, access-controlled answers in real-time.

### The One Rule That Cannot Be Broken
The language model that composes answers **never sees real data values, real table names, real column names, or real identifiers**. It receives only abstracted intent and produces only template responses with placeholder slots (`[SLOT_N]`). Real values are injected into those slots after the LLM has completed its work by a separate, trusted **Compiler layer**.

### Non-Negotiable Principles
*   **LLM-blind data**: Structural enforcement of aliased schemas and abstract intent.
*   **Per-user data scope**: Enforced at the compiler layer with mandatory user ID filters.
*   **Tenant isolation**: Separate namespaces per university at every layer.
*   **Sub-200ms intent cache**: Critical for high-volume results days.
*   **Immutable audit log**: Append-only log of every query and security event.
*   **India data residency**: All inference runs on Azure OpenAI in Central India.

---

## 2. Architecture Overview
ZTA-AI is a seven-layer pipeline where every layer is stateless and independently scalable.

1.  **L1 Client Layer**: PWA interface, handles SSO login and streams tokens.
2.  **L2 Identity + Tenant**: Validates OAuth tokens and builds a signed JWT with user persona/scope.
3.  **L3 Interpreter**: The "security brain." Aliases schema, sanitizes prompts, and extracts intent.
4.  **L4 LLM Engine**: Receives abstract intent/schema. Produces templates with `[SLOT_N]` placeholders.
5.  **L5 Compiler**: Translates logic to real parameterized SQL/API calls. Injects real results into slots.
6.  **L6 Data Sources**: ERPNext (REST API), Google Workspace (Service Account), MySQL/PostgreSQL.
7.  **L7 Admin Dashboard**: Exclusive tool for IT heads to manage users, sources, and policies.

---

## 3. Technology Stack

### Backend Services
*   **Language**: Python 3.11+
*   **Framework**: FastAPI
*   **Task Queue**: Celery + Redis (for sync and async logging)
*   **Cache**: Redis (Intent cache, session cache)
*   **Primary DB**: PostgreSQL 15 (RDS or Cloud SQL)
*   **Vector DB**: Pinecone or Weaviate (for document search)
*   **LLM**: Azure OpenAI (India Central) — GPT-4o / GPT-4o-mini
*   **ORM**: SQLAlchemy 2.0 with Alembic

### Frontend & Infrastructure
*   **Frontend**: Next.js 14 (App Router) with Tailwind CSS + shadcn/ui.
*   **State Management**: Zustand.
*   **Infrastructure**: AWS (ECS Fargate) or GCP (Cloud Run).
*   **CI/CD**: GitHub Actions.
*   **Monitoring**: Sentry (errors), Datadog/Grafana (metrics).

---

## 4. Sprint Plan Summary (Phase 1–3)

### Phase 1: Foundation (Sprints 1–4)
*   **Sprint 1**: Auth, Identity, and Tenant Foundation (Google OAuth, JWT signing).
*   **Sprint 2**: Interpreter — Security Core (Domain gate, prompt sanitizer, schema aliaser).
*   **Sprint 3**: LLM Engine and Template Composer (Azure OpenAI integration, output guard).
*   **Sprint 4**: Compiler, De-tokeniser, and Audit Log (Parameterized queries, real data injection).

### Phase 2: Campus Features (Sprints 5–7)
*   **Sprint 5**: Real Data Connectors (ERPNext, Sheets, MySQL).
*   **Sprint 6**: Chat Interface and Streaming Frontend (PWA, role-aware home screen).
*   **Sprint 7**: Admin Dashboard (User management, schema manager, audit viewer).

### Phase 3: Scale and Polish (Sprints 8–10)
*   **Sprint 8**: Performance and Scale Testing (2,000 simultaneous queries, cache optimization).
*   **Sprint 9**: Security Hardening and Penetration Testing (Cross-tenant/Cross-user testing).
*   **Sprint 10**: Launch Readiness, UAT, and Go-Live.

---

## 5. Definition of Done (Product Level)
*   All 10 sprint acceptance criteria pass in production.
*   P95 latency under 5 seconds for 2,000 concurrent users.
*   Security pen test complete with zero critical/high findings.
*   IT heads can onboard their campus without ZTA-AI team help.
*   5 users from each of the 6 persona types complete UAT without critical issues.
*   Data backup and recovery tested with a successful restore drill.
