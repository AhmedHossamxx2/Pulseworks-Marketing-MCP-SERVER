# Pulseworks Marketing: MCP Server & AI Agent Integration

## 🏢 Company Profile & The Problem

**Pulseworks Marketing** is a high-volume advertising agency responsible for managing complex client campaigns, strict advertising budgets, and multi-platform ad generation.

**The Problem:** Pulseworks wants to leverage an LLM-powered AI agent to automate campaign reporting, draft ad copy, and analyze engagement metrics. However, connecting an AI directly to a live, production marketing database presents massive security and data integrity risks. The agency currently lacks a persistent, structured relational store designed to isolate production data from direct LLM manipulation.

**The Solution:** We are building a robust system utilizing the **Model Context Protocol (MCP)**. This architecture strictly isolates the AI agent from the database by forcing all interactions through an MCP server. This server enforces strict role-based access, defensive data validation, and human-in-the-loop approval workflows before any critical database modifications occur.

---

## 🗄️ Database Architecture & ERD

To safeguard Pulseworks' data, we have designed a strict 6-table relational schema. The physical schema exactly matches the provided Entity-Relationship Diagram (`db/ERD_2.pdf`).

- **`Employees`**: Stores agency staff and their base roles.
- **`Client`**: Tracks active and inactive client profiles.
- **`Campaign`**: Manages campaign platforms and operational statuses (draft, paused, live).
- **`Budgets`**: Enforces strict 1-to-1 limits on daily and total ad spend per campaign.
- **`Advertisements`**: Stores ad copy, enforcing tight character limits (e.g., 50-char headlines) and tracking approval status via an `approver_id` foreign key.
- **`Working`**: An intersection table mapping Employees to specific Campaigns, dictating dynamic project-level permissions (e.g., Director vs. Viewer).

---

## ⚙️ SQL Engine Documentation

**⚠️ CRITICAL REQUIREMENT: This project exclusively uses MySQL.**

- **Engine:** MySQL (Version 8.0+)
- **Why MySQL?** The schema relies on advanced relational features not supported by lightweight file-based engines like SQLite. Specifically, we utilize strict `ENUM` types for status tracking, complex `FOREIGN KEY` constraints (`ON DELETE CASCADE` / `ON DELETE SET NULL`), and strict multi-table relational structures.
- **Configuration:** The server expects to connect to a live MySQL daemon via network port (default `3306`), authenticated via `.env` credentials (e.g., `DB_HOST`, `DB_USER`).
- **Do not use local `.db` files.** Any pull requests attempting to connect via `sqlite3` or generate local `.db` files will fail our integration tests and must be rejected. To set up your local environment, execute the raw `db/schema.sql` and `db/seed.sql` files directly against your MySQL server.

---

## 📡 MCP Protocol Concerns in Action

To ensure safe and reliable AI operations, this project implements nine core MCP protocol concerns integrated directly into the Pulseworks workflow:

### 1. Data & Defensive Operations

- **Defensive Tool Design:** We utilize strict JSON schemas for all server tools, ensuring the AI can only input specific currencies or integer amounts for budgets[cite: 1].
- **Resources:** The server exposes the read-only "Pulseworks Brand Safety Guidelines" file via the `resources/read` endpoint to prevent off-brand ad generation[cite: 1].
- **Prompts:** We implemented a reusable `draft_monthly_client_report` prompt template so the agent can request structured reporting instructions seamlessly[cite: 1].

### 2. Core Protocol & Infrastructure

- **Capability Negotiation:** During startup, the server uses the `initialize` / `initialized` handshake to explicitly declare what capabilities (like sampling and elicitation) it supports before the AI attempts to use them[cite: 1].
- **Transport:** The architecture is designed to start locally using standard input/output (`stdio`), and seamlessly transition to a remote Streamable HTTP connection as the project scales[cite: 1].
- **Notifications:** To handle context switching, the server pushes a `tools/list_changed` alert when a Campaign Director logs in, instantly granting the AI access to higher-tier, budget-altering tools[cite: 1].

### 3. AI Agent & Human-in-the-Loop

- **Elicitation:** We built a critical safety feature where the `increase_campaign_budget` tool pauses mid-action to ask for explicit human sign-off before modifying the database[cite: 1].
- **Sampling:** To ensure quality, we use `sampling/createMessage` to have the model deeply analyze ad engagement metrics before making a recommendation[cite: 1].
- **Progress Tracking:** For heavy operations like a massive audience data pull, we created a tool that intentionally takes a long time and reports intermediate progress back to the user[cite: 1].
