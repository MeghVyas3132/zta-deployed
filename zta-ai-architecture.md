# ZTA-AI — System Architecture
**Zero Trust Architecture — Internal AI Assistant Platform**

---

## 01 — Architectural Layers

ZTA-AI is built on a 7-layer pipeline where no single layer has complete visibility of the entire data lifecycle. This ensures that even if one layer is compromised, the data remains secure.

### Layer 1: Clients (The Interface)
The entry point for all users. No business logic resides here.
*   **Web Client**: Browser-based chat interface for employees (HTTPS/TLS 1.3).
*   **Mobile Client**: iOS / Android native app with device binding (mTLS).
*   **API Client**: Programmatic access for internal systems (API KEY + JWT).
*   **Enterprise SSO**: SAML 2.0 / OIDC integration with corporate identity providers.

### Layer 2: Zero Trust Gate (The Entry Policy)
Every request is re-verified; there is no implicit trust based on network location.
*   **Identity Verifier**: Continuous MFA. No session is implicitly trusted.
*   **Device Trust**: Posture checks, certificate validation, and OS compliance.
*   **Policy Engine**: RBAC + ABAC enforcement of least-privilege access per session.
*   **Audit Logger**: Immutable logs of every prompt, query, and response with user attribution.

### Layer 3: Interpreter (The Abstraction Layer)
Translates natural language into a safe, structured format before it reaches the reasoning engine.
*   **Prompt Sanitizer**: Strips PII, removes injection attempts, and detects prompt attacks.
*   **Intent Mapper**: Converts natural language into structured intent objects (No raw SQL).
*   **Context Abstractor**: Replaces schema, table, and field names with abstract aliases.
*   **Scope Limiter**: Enforces per-user data boundaries before sending to the reasoning engine.

> **[!] ISOLATION BOUNDARY:** The LLM has zero knowledge of database schemas, table names, real field names, or raw data. It only receives abstract intent payloads.

### Layer 4: LLM Reasoning Engine (The DB-Blind Brain)
Performs pure linguistic reasoning without data awareness.
*   **Reasoning Engine**: Performs pure reasoning on sanitized, abstracted intent.
*   **Reasoning Context**: In-session memory using abstract token references only (Ephemeral).
*   **Output Filter**: Blocks attempts to exfiltrate schema info or data in the response (DLP).

### Layer 5: Compiler (The Translator)
The bridge between the abstract reasoning and the physical data store.
*   **Query Compiler**: Translates abstract LLM query logic into real, parameterized DB queries.
*   **Query Validator**: Checks query scope, row-level security (RLS), and prevents aggregation attacks.
*   **Response Decompiler**: Re-aliases raw DB results and filters forbidden columns.
*   **Response Composer**: Formats the final "clean" payload into natural language for the user.

### Layer 6: Secure Database (The Encrypted Store)
The final repository of truth, isolated from the LLM.
*   **Encrypted Data Store**: AES-256 at rest. TLS in transit.
*   **Row-Level Security (RLS)**: Visibility enforced at the DB engine level.
*   **DB Audit Trail**: Tamper-proof logs of every compiled query.
*   **Multi-Tenant Vault**: Org-level isolation; tenants cannot access each other's namespaces.

---

## 02 — Full Request Lifecycle (End-to-End Flow)

1.  **User Prompt**
2.  **Auth Gate** (Identity + Device check)
3.  **Sanitizer** (Injection guard)
4.  **Intent Map** (NL → Abstract Intent)
5.  **LLM Reasoning** (DB-Blind Reasoning)
6.  **Compiler** (Abstract → Parameterized SQL)
7.  **Validator** (RLS + Scope Check)
8.  **Encrypted DB** (Secure Execution)
9.  **Decompiler** (Real Data → Alias Masking)
10. **LLM Format** (Natural Language Composition)
11. **User Response**

---

## 03 — Zero Trust Principles Applied

| Principle | Implementation |
| :--- | :--- |
| **01 // NEVER TRUST** | **Verify Every Request**: No session is implicitly trusted. Every API call re-verifies identity and posture. |
| **02 // LEAST PRIVILEGE** | **Minimal Data Exposure**: The LLM only sees abstract intent; the DB never sees raw prompts. |
| **03 // MICRO-SEGMENT** | **Hard Isolation Layers**: LLM, Interpreter, Compiler, and DB run in isolated execution zones. |
| **04 // ASSUME BREACH** | **Continuous Monitoring**: All layers emit to a central SIEM with anomaly detection. |

---

## 04 — Layer Color Legend (Technical Map)
*   **Yellow**: Zero Trust Gate / Authentication
*   **Purple**: Interpreter / Abstraction
*   **Orange**: LLM Engine (Database-Blind)
*   **Blue**: Compiler / Decompiler
*   **Green**: Encrypted Database Store
