# Clinical Copilot — Backend

> AI-powered clinical decision support and triage agent for resource-constrained
> healthcare systems. Built for the Google Cloud Rapid Agent Hackathon (Arize track).

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Docker](#docker)
- [Database Migrations](#database-migrations)
- [API Overview](#api-overview)
- [Agent Design](#agent-design)
- [Observability](#observability)
- [Self-Improvement Loop](#self-improvement-loop)
- [Switching LLM Providers](#switching-llm-providers)
- [Switching Agent Frameworks](#switching-agent-frameworks)
- [Troubleshooting](#troubleshooting)

---

## Overview

Clinical Copilot reduces cognitive load on doctors in Nigerian public hospitals
by automating the groundwork before and after each consultation.

**Before the doctor walks in:**
- Accepts patient intake via web form
- Scores urgency (1–5) and flags critical patients
- Generates a ranked differential diagnosis grounded in FMOH/WHO guidelines
- Runs a drug interaction check against the national formulary
- Assembles a 60-second handoff brief

**After the consultation:**
- Drafts a SOAP clinical note from the ambient transcript
- Generates referral letters and discharge summaries on demand

**Continuously:**
- Every triage decision is traced in Arize Phoenix via OpenInference
- An LLM-as-Judge evaluator scores each trace
- The agent rewrites its own prompt based on failure patterns

---

## Architecture

```
Patient / Nurse
    │ POST /api/v1/intake/
    ▼
FastAPI Backend
    ├── TriageAgent (Google ADK + Gemini)
    │       ├── urgency_score tool
    │       ├── differential_diagnosis tool
    │       ├── drug_interaction_check tool
    │       └── assemble_brief tool
    │               └── grounded by Vertex AI Search
    │
    ├── DocumentationAgent (Google ADK + Gemini)
    │       ├── draft_clinical_note tool
    │       ├── draft_referral tool
    │       └── draft_discharge tool
    │
    └── EvaluatorAgent (Google ADK + Gemini)
            ├── get_traces tool  → Phoenix MCP
            ├── get_annotations tool → Phoenix MCP
            └── upsert_prompt tool → Phoenix MCP
                    └── self-improvement loop
```

**Dependency flow:**

```
API Router
  └── Use Case
        └── Service
              └── Repository → Database
              └── Agent → LLM + Tools + Knowledge Store
              └── MCP Client → Phoenix
```

---

## Tech Stack

| Concern | Technology |
|---|---|
| API framework | FastAPI (async) |
| Agent runtime | Google ADK |
| LLM | Gemini 2.5 Flash (swappable to OpenAI) |
| Observability | Arize Phoenix + OpenInference |
| Database | PostgreSQL + SQLAlchemy (async) + Alembic |
| Cache | Redis |
| Knowledge store | Vertex AI Search (static fallback for local dev) |
| DI container | dependency-injector |
| Settings | Pydantic BaseSettings |
| Containerisation | Docker + docker-compose |

---

## Project Structure

```
backend/
├── main.py                         # App factory, lifespan, middleware, routers
├── requirements.txt
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── alembic.ini
├── alembic/
│   └── versions/
│
├── src/
│   ├── api/                        # HTTP layer — routers + schemas only
│   │   ├── intake/
│   │   ├── triage/
│   │   ├── consult/
│   │   └── evaluation/
│   │
│   ├── application/                # Use cases — orchestrate services
│   │   ├── triage_patient.py
│   │   ├── generate_note.py
│   │   ├── generate_referral.py
│   │   ├── generate_discharge.py
│   │   └── evaluate_agent.py
│   │
│   ├── domain/                     # Pure business logic — no infra imports
│   │   ├── patient/
│   │   ├── triage/
│   │   ├── documentation/
│   │   ├── evaluation/
│   │   └── knowledge/
│   │
│   ├── core/                       # Framework-agnostic abstractions
│   │   ├── agents/
│   │   ├── tools/
│   │   └── mcp/
│   │
│   ├── infrastructure/             # Concrete implementations
│   │   ├── agents/
│   │   │   ├── adk/                # ADK agents + tool adapters
│   │   │   └── langgraph/          # Placeholder for future swap
│   │   ├── cache/
│   │   ├── db/
│   │   ├── knowledge/
│   │   ├── language_models/
│   │   ├── mcp/
│   │   ├── observability/
│   │   ├── repository/
│   │   ├── services/
│   │   └── tools/
│   │       ├── triage/
│   │       ├── documentation/
│   │       └── evaluation/
│   │
│   └── config/
│       ├── base.py                 # Settings + get_settings()
│       ├── development.py
│       ├── staging.py
│       ├── production.py
│       └── dependency_injection/
│           └── container.py        # Single source of DI wiring
│
├── tests/
│   ├── unit/
│   └── e2e/
│
└── utils/
    └── logger.py
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | |
| Node.js | 18+ | Required for Phoenix MCP subprocess |
| PostgreSQL | 15+ | |
| Redis | 7+ | |
| Google Cloud SDK | latest | For Vertex AI + ADK |
| Gemini API key | — | From Google AI Studio or GCP |
| Arize Phoenix account | — | Free at app.phoenix.arize.com |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all required values.

```bash
cp .env.example .env
```

### Full variable reference

```bash
# ── App ───────────────────────────────────────────────────────────────────────
APP_ENV=development           # development | staging | production
DEBUG=true
VERSION=0.1.0-dev
PORT=8000
LOG_LEVEL=DEBUG
API_V_STR=/api/v1
CORS_ORIGINS=["*"]

# ── Database ──────────────────────────────────────────────────────────────────
SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@localhost:5432/clinical_copilot

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_PROVIDER=gemini           # gemini | openai
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
OPENAI_API_KEY=               # only needed if LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o

# ── GCP ───────────────────────────────────────────────────────────────────────
GCP_PROJECT=your-gcp-project-id
GCP_LOCATION=us-central1
VERTEX_DATASTORE_ID=          # leave empty to use static knowledge store locally

# ── Google Service Account ────────────────────────────────────────────────────
# Option 1 — paste full JSON as single line (recommended for containers)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}

# Option 2 — path to a local file
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json

# ── Phoenix / Arize ───────────────────────────────────────────────────────────
PHOENIX_MODE=noop             # noop | local | cloud
PHOENIX_API_KEY=              # required when PHOENIX_MODE=cloud
PHOENIX_PROJECT_NAME=clinical-copilot
PHOENIX_CLOUD_ENDPOINT=https://app.phoenix.arize.com
PHOENIX_LOCAL_ENDPOINT=http://localhost:6006
PHOENIX_TRIAGE_PROMPT_NAME=triage-system-prompt
```

### Phoenix mode guide

| Mode | When to use | Requires |
|---|---|---|
| `noop` | Local dev, no Phoenix account | Nothing |
| `local` | Local dev with full tracing | Docker Phoenix container |
| `cloud` | Staging and production | Phoenix API key |

---

## Local Development

### 1. Create and activate virtual environment

```bash
python -m venv triage_env
source triage_env/bin/activate   # Windows: triage_env\Scripts\activate
```

### 2. Install dependencies

```bash
make install
# or
pip install -r requirements.txt
```

### 3. Verify Node.js for Phoenix MCP

```bash
make node-check
```

### 4. Start infrastructure services

```bash
# PostgreSQL + Redis via docker-compose (infra only)
docker-compose up postgres redis -d
```

### 5. Set up environment

```bash
cp .env.example .env
# Edit .env — minimum required:
# SQLALCHEMY_DATABASE_URI
# GEMINI_API_KEY
# PHOENIX_MODE=noop   (for local dev without Phoenix)
```

### 6. Run migrations

```bash
make migrate
```

### 7. Start the development server

```bash
make dev
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/docs   # Swagger UI
```

---

## Docker

### Run everything with docker-compose

```bash
# Build and start all services
make up

# View logs
make compose-logs

# Stop
make down
```

### Build and run API container only

```bash
make build
make run
```

### Useful container commands

```bash
make shell              # open shell in running container
make logs               # tail container logs
make health             # curl health endpoint
```

---

## Database Migrations

```bash
# Apply all pending migrations
make migrate

# Create a new migration after changing models
make migrate-create msg="add phoenix_trace_id to triage_results"

# Reset database (development only — destroys all data)
make db-reset
```

### Alembic setup

`alembic.ini` must point to your database:

```ini
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/clinical_copilot
```

Or use an environment variable override in `alembic/env.py`:

```python
from src.config.base import get_settings
config.set_main_option("sqlalchemy.url", get_settings().SQLALCHEMY_DATABASE_URI)
```

---

## API Overview

All endpoints are prefixed with `/api/v1/`.

Base URL (local): `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/api/v1/docs`

### Endpoint groups

| Group | Prefix | Purpose |
|---|---|---|
| Intake | `/api/v1/intake` | Patient intake submission |
| Triage | `/api/v1/triage` | Triage pipeline and results |
| Consult | `/api/v1/consult` | Documentation generation |
| Evaluation | `/api/v1/eval` | Agent evaluation pipeline |
| Health | `/health`, `/health/agents` | Liveness and readiness |

---

## Agent Design

### TriageAgent

Triggered by a new intake. Runs four tools in sequence:

1. `urgency_score` — assigns urgency level 1–5
2. `differential_diagnosis` — top 5 diagnoses grounded in FMOH/WHO data
3. `drug_interaction_check` — flags interactions against the national formulary
4. `assemble_brief` — compiles a 60-second doctor handoff card

### DocumentationAgent

Triggered by doctor action post-consultation:

- `draft_clinical_note` — SOAP note from transcript
- `draft_referral` — formal referral letter
- `draft_discharge` — plain-language discharge summary

### EvaluatorAgent

Runs nightly (or on demand via `/api/v1/eval/run`):

1. Pulls triage traces from Phoenix via MCP
2. Fetches doctor override annotations
3. Scores each trace with LLM-as-Judge
4. Clusters failure patterns
5. Rewrites and upserts the triage system prompt if rolling average < 7.0

---

## Observability

Every ADK tool call is automatically traced via `openinference-instrumentation-google-adk`.

Traces appear in Phoenix at `app.phoenix.arize.com` under project `clinical-copilot`.

Each triage session produces:

```
[root] triage_patient
  ├── urgency_score      (input: symptoms, output: level + reasoning)
  ├── differential_diagnosis  (input: patient profile, output: ranked Dx)
  ├── drug_interaction_check  (input: medications, output: flags)
  └── assemble_brief     (input: all above, output: brief card)
```

### Running Phoenix locally

```bash
docker run -p 6006:6006 arizephoenix/phoenix:latest
# Then set PHOENIX_MODE=local in .env
```

---

## Self-Improvement Loop

```
Nightly or manual trigger (/api/v1/eval/run)
  │
  ├── GetTracesTool → Phoenix MCP get-spans (last 24h)
  ├── GetAnnotationsTool → doctor override annotations
  ├── LLM-as-Judge scoring (relevance / completeness / ranking / safety)
  ├── Failure pattern clustering
  │
  └── IF rolling_avg < 7.0:
        EvaluatorAgent drafts improved prompt section
        UpsertPromptTool → Phoenix prompt registry (tagged "production")
        TriageAgent loads new prompt on next run
```

---

## Switching LLM Providers

Change one env variable:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o
```

No code changes. The container's `_make_llm_client` factory handles the swap.

---

## Switching Agent Frameworks

1. Implement `IAgent` in `src/infrastructure/agents/langgraph/`
2. Update three providers in `container.py`:
```python
   triage_agent = providers.Factory(_build_triage_agent, factory=langgraph_factory)
```
3. No changes to use cases, services, domain, or API layer.

---

## Troubleshooting

### Redis shows degraded

Check that `redis_client` is `providers.Singleton` not `providers.Factory` in
`container.py`. A Factory creates a new unconnected instance on every call.

### Phoenix MCP unavailable

Run the inspector to confirm tool names:
```bash
npx @modelcontextprotocol/inspector npx @arizeai/phoenix-mcp
```

### Lifespan not running

Ensure uvicorn points at `app` (the Starlette root) not `api_app`. The
lifespan must be on the same object uvicorn starts.

### GCP credentials error

```bash
# Verify the service account JSON is valid
echo $GOOGLE_SERVICE_ACCOUNT_JSON | python -m json.tool
```

### Vertex AI datastore not configured

Set `VERTEX_DATASTORE_ID=` (empty) — the app automatically falls back to
`StaticKnowledgeStore` which uses pre-loaded Nigerian clinical guidelines.

### Database connection refused

```bash
docker-compose up postgres -d
make migrate
```