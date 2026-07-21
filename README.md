# NT MemoryVault

**Sovereign AI Continuity Platform for persistent, governed multi-agent memory.**

NT MemoryVault makes AI agents remember customers, cases, decisions, and work context across sessions, models, and channels—while enforcing tenant isolation, access policy, auditability, retention, and deletion.

## MVP scope

- Persistent memory API
- Cross-agent handover
- Tenant and agent isolation
- Policy-controlled retrieval
- Audit trail for read/write/deny/delete events
- Right-to-be-forgotten by subject
- Two-agent demo: Support Agent → Sales Agent
- Local/private deployment with Docker Compose

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

API documentation: `http://localhost:8000/docs`

Run the end-to-end demo:

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

Every request uses these headers:

- `X-Tenant-ID`
- `X-Agent-ID`
- `X-Agent-Role`

## Product principle

> AI remembers only what it should remember, shares only what it is allowed to share, and forgets when ordered to forget.

## Initial architecture

```text
Agent / Application
        │
FastAPI Memory API
        │
Policy Engine ── Audit Log
        │
PostgreSQL + pgvector
```

## Roadmap

1. MVP API, policy, audit, deletion
2. Semantic embeddings through local Qwen/OpenAI-compatible endpoint
3. Memory consolidation and conflict resolution
4. Web governance dashboard
5. MCP, LangChain, LlamaIndex, and Agent framework adapters
6. AD/LDAP, SIEM, BYOK, private network, dedicated tenant

## License

Proprietary evaluation prototype for NT AIaaS / Hackathon development.
