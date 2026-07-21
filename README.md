# NT MemoryVault

**Sovereign AI Continuity Platform for persistent, governed multi-agent memory.**

NT MemoryVault makes AI agents remember customers, cases, decisions, and work context across sessions, models, and channels—while enforcing tenant isolation, access policy, auditability, retention, and deletion.

## MVP delivered

- Persistent memory API
- Cross-agent handover
- Tenant and agent isolation
- Policy-controlled retrieval
- Audit trail for read/write/deny/delete events
- Right-to-be-forgotten by subject
- Two-agent demo: Support Agent → Sales Agent
- White + electric-blue governance dashboard
- Local/private deployment with Docker Compose
- GitHub Actions compile and FastAPI import check

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Demo dashboard: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

For access through a server IP or domain, set `CORS_ORIGINS` in `.env` to the dashboard origin, for example `http://203.0.113.10:3000`.

## 90-second demo

The dashboard runs the complete story in three clicks:

1. **Reset & Seed** — Support Agent using Qwen stores one shared customer preference and one restricted support note.
2. **Sales Retrieve** — Sales Agent using another model receives only the approved context; the restricted memory is denied and logged.
3. **Delete Customer** — Privacy Admin executes Right to be Forgotten; subsequent retrieval returns no customer memory.

Command-line version:

```bash
python demo/demo_flow.py
```

## Core API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/v1/memories` | Store a governed memory |
| `POST` | `/v1/memories/search` | Retrieve memories allowed by policy |
| `GET` | `/v1/audit` | Inspect memory access history |
| `DELETE` | `/v1/subjects/{subject_id}/memories` | Delete all memories for a subject |
| `GET` | `/health` | Health check |

Every governed request uses:

- `X-Tenant-ID`
- `X-Agent-ID`
- `X-Agent-Role`

## Memory object

Each record includes tenant, subject, source agent, scope, memory type, content, confidence, sensitivity, allowed roles, validity period, expiry, source, and metadata.

The first MVP uses lexical relevance scoring so it runs without an external model. The next retrieval provider will use local embeddings through an OpenAI-compatible Qwen endpoint and PostgreSQL/pgvector.

## Product principle

> AI remembers only what it should remember, shares only what it is allowed to share, and forgets when ordered to forget.

## Architecture

```text
Agent / Application
        │
FastAPI Memory API
        │
Policy Engine ───── Audit Trail
        │                 │
PostgreSQL / pgvector   Governance Dashboard
```

## Next build order

1. Local Qwen embedding provider + pgvector semantic retrieval
2. Memory consolidation, conflict resolution, and superseding records
3. MCP server and framework adapters
4. API keys, JWT, AD/LDAP, and per-tenant policy administration
5. SIEM export, BYOK encryption, retention jobs, and dedicated tenant deployment

## License

Proprietary evaluation prototype for NT AIaaS / Hackathon development.
