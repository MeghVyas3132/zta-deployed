# ZTA-AI — Complete Explainer
**Secure Enterprise AI Platform with Zero Trust Data Isolation**

---

## 01 — The Core Idea: The AI is Kept Blind

Most companies are hesitant to use internal AI because an assistant connected to a database could accidentally expose sensitive information. ZTA-AI solves this by keeping the AI (the LLM) completely isolated from the raw data.

### The Request Lifecycle
1.  **Employee types a question**: e.g., "What is our current NPL ratio by branch?"
2.  **Zero Trust Gate**: Every request re-verifies identity, role, and device posture.
3.  **Interpreter**: Strips injections and replaces real table names with abstract aliases (e.g., `loans_2024` → `source_A`).
4.  **LLM Engine**: Receives only the abstract intent. It performs reasoning without ever seeing the database schema or raw data.
5.  **Compiler**: Translates the abstract logic back into a safe, parameterized SQL query in a trusted zone.
6.  **Encrypted Database**: The real query runs. Results are re-aliased before being passed back to the AI.
7.  **LLM Formatting**: The AI takes the masked results and writes a friendly, natural language answer.
8.  **Employee receives response**: A clean, natural language answer with a full, tamper-proof audit trail.

---

## 02 — RBAC / ABAC: Access Control

Every query is attached to a signed JWT token ("digital badge") that defines exactly what data the user can access.

### Role-Based Access Control (RBAC)
*   **HR Manager**: Access to salaries, leave, and performance. No access to revenue or source code.
*   **Finance Analyst**: Access to revenue and P&L. No access to individual salaries or legal files.
*   **Senior Engineer**: Access to code repos and logs. No access to HR or financial data.
*   **C-Suite**: Access to aggregated cross-dept KPIs. No access to individual PII or raw DB.

### Attribute-Based Access Control (ABAC)
*   **Time**: Access for certain roles is blocked outside of business hours (9 am – 7 pm).
*   **Location**: Sensitive data access requires a corporate network or VPN.
*   **Sensitivity**: Fields like SSN or bank accounts are always masked for analyst roles.
*   **Anomaly**: Rapid querying of sensitive data triggers automatic session revocation.

---

## 03 — Data Integration

ZTA-AI connects to virtually any enterprise data source through three main paths:
1.  **No-code UI**: A dashboard wizard for non-technical admins.
2.  **SDK / API**: Full control for developers (Python, Node, Java).
3.  **On-prem Agent**: A Docker container for air-gapped or highly regulated environments.

### Supported Sources
*   **Databases**: PostgreSQL, MySQL, MSSQL, Oracle, Snowflake, MongoDB.
*   **Cloud Storage**: AWS S3, Google Cloud, Azure Blob, BigQuery.
*   **SaaS Tools**: Slack, Jira, Salesforce, SAP, Microsoft 365, Google Workspace.
*   **Files**: PDF, Excel/CSV, Word, JSON/XML.

---

## 04 — Market Scope & Opportunity

ZTA-AI addresses a $133B combined market of Conversational AI and Zero Trust Security.

### Target Verticals
1.  **BFSI**: Banks and fintechs (Highest priority due to RBI/SEBI compliance).
2.  **Healthcare**: HIPAA-compliant patient/billing data isolation.
3.  **Government**: NSA Zero Trust mandates and on-prem requirements.
4.  **Legal**: Attorney-client privilege and matter-level silos.

### Pricing Model
*   **Starter ($199/mo)**: Up to 50 users, 2 sources.
*   **Business ($999/mo)**: Up to 500 users, 10 sources, full RBAC/ABAC.
*   **Enterprise (Custom)**: Unlimited users, on-prem deployment, SLAs.

---

## 05 — BFSI Strategy: Starting with Banking

Banks have the highest willingness to pay and the strictest regulatory requirements (RBI FREE-AI 2025, DPDP Act 2023).

### Internal Use Cases
*   **Risk Analyst**: Querying NPL ratios across branches.
*   **Compliance Officer**: Detecting AML threshold breaches.
*   **Treasury Desk**: Monitoring ALM gaps and SLR/CRR concerns.

### Sales Strategy
The pitch focuses on cost-efficiency (e.g., ₹50L/year for ZTA-AI vs. ₹90L/year for 3 analysts) and guaranteed compliance. The roadmap targets NBFCs and fintechs first, moving upstream to private and public banks.
