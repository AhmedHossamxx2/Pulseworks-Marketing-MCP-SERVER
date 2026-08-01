Here is the complete, comprehensive `README.md` file tailored specifically to your codebase, team structure, and protocol requirements. It incorporates all of your project code, SQL specs, protocol implementations, tool classification matrices, and runtime logs.

Copy and paste the markdown content below directly into your project's `README.md`.

---

# Pulseworks Marketing: MCP Server & AI Agent Integration

## 🏢 Company Profile & The Problem

**Pulseworks Marketing** is a high-volume advertising agency responsible for managing complex client campaigns, strict advertising budgets, multi-platform ad generation, and demographic analytics.

**The Problem:** Pulseworks wanted to leverage an LLM-powered AI agent to automate campaign reporting, draft ad copies, analyze engagement metrics, and adjust daily spend limits. However, giving an LLM direct, unstructured access (or raw SQL execution privileges) to a live production database presents massive security, compliance, and financial risks:

* **Arbitrary Writes / SQL Injection:** A hallucinated SQL update could drop production tables or corrupt client campaign states.
* **Financial Risk:** Unrestricted budget modifications could exceed client contracts or spend thresholds.
* **Brand & Regulatory Damage:** Non-compliant ad copies could violate brand safety policies or industry regulations.

**The Solution:** We constructed a secure operational architecture powered by the **Model Context Protocol (MCP)**. Sitting between the LLM and the production MySQL database, the **Pulseworks Marketing MCP Server** acts as an operational firewall. It enforces capability negotiation, 3-layer defensive validation, dynamic role-based authorization, human-in-the-loop elicitation, progress reporting, and read-only resource access before any database read or write takes place.

---

## 👥 Team Roles & Task Division

To ensure clean modularity and equal project ownership across the team, work was split across repository directories and specific MCP protocol concerns:

| Team Member | Folder Focus | Role & Core Responsibilities | Owned Protocol Concerns |
| --- | --- | --- | --- |
| **Team Member 1** | `db/`<br>

<br>`mcp_server/` | **Data & Defensive Operations Lead**<br>

<br>Designed relational schema & ERD; implemented defensive tool schemas (`validation.py`), Brand Safety resources, and reporting prompt templates. | • **Defensive Tool Design**<br>

<br>• **Resources** (`guidelines://brand_safety`)<br>

<br>• **Prompts** (`draft_monthly_client_report`) |
| **Team Member 2** | `mcp_server/` | **Core Protocol & Infrastructure Lead**<br>

<br>Built FastMCP server initialization, managed capability negotiation, implemented dynamic role-change notification pushes, and handled network transport evolution. | • **Capability Negotiation** (`initialize`)<br>

<br>• **Transport Evolution** (`stdio` $\rightarrow$ `SSE`)<br>

<br>• **Notifications** (`tools/list_changed`) |
| **Team Member 3** | `Agent/` | **AI Agent & Human-in-the-Loop Lead**<br>

<br>Constructed LangChain agent client session (`client.py`), context-aware tool invocation wrappers, progress tracking handlers, and human sign-off elicitation. | • **Elicitation** (`elicitation/create`)<br>

<br>• **Sampling** (`create_message`)<br>

<br>• **Progress Tracking** (`report_progress`) |

---

## 🗄️ Database Architecture & ERD

To safeguard Pulseworks' data, we designed a strict 6-table relational schema. The physical schema exactly matches the provided Entity-Relationship Diagram (`db/ERD_2.pdf`).

```
 +------------------+        +------------------+        +------------------+
 |    Employees     |        |      Client      |        |     Campaign     |
 +------------------+        +------------------+        +------------------+
 | PK employee_id   |        | PK client_id     |        | PK campaign_id   |
 |    emp_name      |<-------|    client_name   |<-------| FK client_id     |
 |    emp_role      |        |    industry      |        |    campaign_name |
 +------------------+        +------------------+        |    status        |
          |                           |                  +------------------+
          |                           |                           |
          v                           v                           v
 +------------------+        +------------------+        +------------------+
 |     Working      |        |  Advertisements  |        |     Budgets      |
 +------------------+        +------------------+        +------------------+
 | PK working_id    |        | PK ad_id         |        | PK budget_id     |
 | FK employee_id   |        | FK campaign_id   |        | FK campaign_id   |
 | FK campaign_id   |        | FK approver_id   |        |    daily_limit   |
 |    role_in_proj  |        |    headline      |        |    currency      |
 +------------------+        +------------------+        +------------------+

```

### Table Breakdown:

* **`Employees`**: Stores agency staff and system-wide default roles.
* **`Client`**: Tracks active and inactive corporate client accounts.
* **`Campaign`**: Manages campaign platforms and operational statuses (`draft`, `active`, `paused`, `archived`).
* **`Budgets`**: Enforces strict 1-to-1 limits on daily and total ad spend per campaign.
* **`Advertisements`**: Stores ad copy, enforcing tight character limits and tracking sign-offs via `approver_id`.
* **`Working`**: Mapping table assigning staff to campaigns with specific project roles (`Director` vs. `Viewer`).

---

## ⚙️ SQL Engine Documentation

**⚠️ CRITICAL REQUIREMENT: This project exclusively relies on MySQL 8.0+.**

* **Engine:** MySQL (Version 8.0+)
* **Why MySQL?** The schema relies on advanced relational features not supported by lightweight file-based engines like SQLite:
* Strict `ENUM` types for campaign/ad status tracking.
* Foreign Key constraint cascading (`ON DELETE CASCADE` / `ON DELETE SET NULL`).
* Strict transactional isolation for budget modifications.


* **Configuration:** The server connects to a live MySQL daemon via network port (default `3306`), configured via `.env`:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=pulseworks_db
DB_USER=root
DB_PASSWORD=your_secure_password

```


* **Local Setup:** Execute `db/schema.sql` followed by `db/seed.sql` on your local MySQL server instance. Do not generate or commit SQLite `.db` files.

---

## 🌐 Protocol Concerns & Architectural Implementation

The server implements all 8 MCP protocol concerns required by the enterprise specification. Each concern has been placed in `mcp_server/` and `Agent/` with clear execution boundaries:

### 1. Capability Negotiation (`initialize`)

During session establishment, the client and server exchange explicit capability flags. The server exposes supported protocol features (`tools.listChanged = True`, `resources`, `prompts`, `sampling`), and the client verifies these flags using `check_client_capability(...)` before triggering capabilities.

### 2. Transport Evolution (`stdio` $\rightarrow$ `Streamable HTTP / SSE`)

* **Development Phase (`stdio`):** Used during local debugging for isolated server execution.
* **Production Deployment (`Streamable HTTP / SSE`):** Transitioned in git history to FastMCP SSE transport listening on `[http://0.0.0.0:8000/sse](http://0.0.0.0:8000/sse)`.
* **Justification:** Local `stdio` cannot support multi-location agency branches. Streamable HTTP over SSE enables multi-user remote AI agents to connect over secure network endpoints using session tokens (`session_id`).

### 3. Defensive Tool Design (3-Layer Guardrails)

Write operations (`request_budget_update`) pass through 3 sequential validation layers:

1. **Layer 1 (Schema Validation):** `validation.py` enforces JSON Schema typing, bounds (`minimum: 10.0`, `maximum: 10000.0`), `enum: ["USD", "EUR", "GBP"]`, and `additionalProperties: False`.
2. **Layer 2 (Handler RBAC Check):** `tools.py` checks active session state (`session_state["emp_role_in_campaign"]`). Rejects non-`Director` roles with `FORBIDDEN_ROLE`.
3. **Layer 3 (MySQL Verification):** `database.py` verifies campaign existence and prevents modifications to `archived` campaigns (`REJECTED_BUSINESS_LOGIC`).

### 4. Resources & Parameterized Prompts

* **Resource (`guidelines://brand_safety`):** Read-only Brand Safety Guidelines located in `mcp_server/resources/brand_safety_guidelines.md` are exposed via `resources/read`. The model fetches policy documents as context without executing function tools.
* **Prompt (`draft_monthly_client_report`):** Exposed via `prompts/get`, accepting `client_name` and `reporting_month` parameters to format executive client reports.

### 5. Progress Tracking (`report_progress`)

Long-running demographic batch fetches (`pull_audience_demographics`) process records in batches of 250. It yields real-time progress events using `await ctx.report_progress(progress=total_fetched, total=sample_size)`, streaming progress percentages (`25%` $\rightarrow$ `50%` $\rightarrow$ `75%` $\rightarrow$ `100%`) back to the client interface.

### 6. Dynamic Notifications (`tools/list_changed`)

When a user's role elevates mid-session (e.g., `Viewer` $\rightarrow$ `Director`), the server emits a `notifications/tools/list_changed` push signal over the active SSE connection. The client catches this notification and updates available tools without disconnecting.

### 7. Elicitation (`elicitation/create`)

For high-value spend increases exceeding threshold limits, tool execution pauses mid-action to request explicit human confirmation (`elicitation/create`), ensuring an automated agent cannot execute unratified financial decisions.

### 8. LLM Sampling (`create_message`)

In `analyze_ad_performance_and_recommend`, the server issues a callback (`ctx.session.create_message`) to the host model. The host model evaluates ad metrics and synthesizes strategic recommendations before returning the final tool output.

---

## 📊 Tool Classification & Safety Matrix

| Tool / Resource Name | Type | Access Level | Validation & Guardrails | Elicitation / Sampling Trigger | Client Fallback Behavior |
| --- | --- | --- | --- | --- | --- |
| `check_system_capabilities` | Diagnostic Tool | Read-Only (All Roles) | None | None | Returns baseline server status. |
| `pull_audience_demographics` | Data Tool | Read-Only (All Roles) | Numeric batch parameters; batch sleeping | Progress reporting via `report_progress` | Executes synchronously without progress reporting. |
| `analyze_ad_performance_and_recommend` | Analytical Tool | Read-Only (All Roles) | MySQL Campaign ID existence check | LLM Sampling via `ctx.session.create_message` | Falls back to static template reasoning. |
| `request_budget_update` | Write / State Tool | Restricted (`Director` Only) | **3-Layer:** Schema validation, RBAC role check, MySQL status check | Elicitation trigger for high daily spend | Returns `REJECTED_UNAUTHORIZED` error response. |
| `guidelines://brand_safety` | Resource | Read-Only (All Roles) | Static Markdown File | None | Content unavailable fallback text. |
| `draft_monthly_client_report` | Prompt | Read-Only (All Roles) | Parameter String Formatting | None | Returns default unparameterized template. |

---

## 📂 Repository Structure

```text
Pulseworks-Marketing-MCP-SERVER/
├── db/
│   ├── ERD_2.pdf                   # Official Entity-Relationship Diagram
│   ├── schema.sql                  # MySQL table creation scripts
│   └── seed.sql                    # Production seed data (normal and edge cases)
├── mcp_server/
│   ├── __init__.py                 # MCP Server Package Initializer
│   ├── server.py                   # FastMCP Server Entrypoint & Capability Declarations
│   ├── tools.py                    # Tool definitions (Defensive, Progress, Sampling)
│   ├── database.py                 # MySQL Context Manager Connection Handler
│   ├── validation.py               # JSON Schema Definitions & Guardrail logic
│   └── resources/
│       └── brand_safety_guidelines.md # Read-only Brand Safety Policy Document
├── Agent/
│   ├── agent_core.py               # LangChain Agent Execution Loop & Context Tool Injector
│   ├── client.py                   # MCP SSE Client, Handshake & Progress Listener
│   ├── main.py                     # Standalone Local CLI Interface
│   └── utils/
│       ├── config.py               # Environment Configuration Loader
│       └── llm.py                  # Gemini LLM Initialization Setup
├── .env                            # Environment Credentials (Git Ignored)
├── pyproject.toml                  # Project Dependencies & UV Package Spec
└── README.md                       # Complete Architectural & Protocol Documentation

```

---

## 🚀 Installation & Setup Guide

### 1. Prerequisites

* Python 3.10+
* MySQL Server 8.0+ running on port `3306`
* `uv` package manager (`pip install uv`)

### 2. Environment Configuration

Create a `.env` file in the root project directory:

```env
# Gemini API Key
GEMINI_API_KEY=AIzaSyYourActualKeyHere

# MySQL Database Settings
DB_HOST=localhost
DB_PORT=3306
DB_NAME=pulseworks_db
DB_USER=root
DB_PASSWORD=your_password

# MCP Transport Configuration
MCP_TRANSPORT_TYPE=sse
MCP_SERVER_HTTP_URL=http://localhost:8000/sse

```

### 3. Database Initialization

Import the schema and seed data into your MySQL server:

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS pulseworks_db;"
mysql -u root -p pulseworks_db < db/schema.sql
mysql -u root -p pulseworks_db < db/seed.sql

```

### 4. Install Dependencies

```powershell
uv pip install -e .

```

---

## 🧪 Testing & Execution Protocol

### Step 1: Launch the MCP Server (Terminal 1)

Start the FastMCP server in SSE mode:

```powershell
uv run python -m mcp_server.server

```

*Expected Terminal Output:*

```text
INFO:     Started server process [...]
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     SSE endpoint listening at http://0.0.0.0:8000/sse

```

### Step 2: Execute the Agent Client Session (Terminal 2)

Run the agent client to initiate the protocol handshake and query execution:

```powershell
uv run python Agent/client.py

```

*Actual Terminal Execution Log:*

```text
INFO:PulseworksMCPClient:Connecting to Pulseworks MCP Server via SSE at http://localhost:8000/sse...
INFO:httpx:HTTP Request: GET http://localhost:8000/sse "HTTP/1.1 200 OK"
INFO:PulseworksMCPClient:Initiating MCP Handshake over HTTP/SSE...
INFO:httpx:HTTP Request: POST http://localhost:8000/messages/?session_id=0998c5926e7c4b7bb810704c1cc2fdfa "HTTP/1.1 202 Accepted"
INFO:PulseworksMCPClient:✅ Connected to MCP Server: Pulseworks Marketing MCP Server
INFO:PulseworksMCPClient:Server Capabilities: experimental={} logging=LoggingCapability() prompts=PromptsCapability(listChanged=True) resources=ResourcesCapability(subscribe=False, listChanged=True) tools=ToolsCapability(listChanged=True) completions=None tasks=None extensions={'io.modelcontextprotocol/ui': {}}
INFO:httpx:HTTP Request: POST http://localhost:8000/messages/?session_id=0998c5926e7c4b7bb810704c1cc2fdfa "HTTP/1.1 202 Accepted"
INFO:httpx:HTTP Request: POST http://localhost:8000/messages/?session_id=0998c5926e7c4b7bb810704c1cc2fdfa "HTTP/1.1 202 Accepted"
INFO:PulseworksMCPClient:Discovered 4 tools over SSE: ['check_system_capabilities', 'request_budget_update', 'pull_audience_demographics', 'analyze_ad_performance_and_recommend']
INFO:PulseworksMCPClient:Running Agent Query: 'Pull audience demographics for segment 'segment_alpha' with sample size 1000'
INFO:httpx:HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://localhost:8000/messages/?session_id=0998c5926e7c4b7bb810704c1cc2fdfa "HTTP/1.1 202 Accepted"
INFO:httpx:HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent "HTTP/1.1 200 OK"
INFO:PulseworksMCPClient:Agent Output:
[{'type': 'text', 'text': 'Audience demographics for segment **`segment_alpha`** have been successfully retrieved. Here is the summary:\n\n* **Segment ID:** segment_alpha\n* **Total Records Retrieved:** 1,000\n* **Primary Age Group:** 25–34\n* **Top Geography:** North America\n* **Status:** Success (Long-running process)'}]

```