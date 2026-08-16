# InsightForge — Multi-Agent AI Research Assistant

> A production-grade research platform where a user submits a question and a
> team of AI agents plans, searches the web, extracts evidence, fact-checks,
> cites, writes and reviews a final report — streamed live to the frontend.

---

## Project Purpose

InsightForge turns a single research question into a **structured, cited,
fact-checked report**. Behind the scenes a LangGraph pipeline coordinates
multiple specialized agents (planner, researcher, evidence extractor, claim
extractor, fact-checker, citator, confidence scorer, writer, critic). The
FastAPI backend exposes this pipeline as a clean, observable HTTP API, and a
future Next.js frontend (Phase 2E) will render the live research experience.

The backend is **Phase 2D complete** and is frontend-integration ready. This
README is part of a **UI handoff package** so that another coding agent
(Antigravity) can build the frontend without reverse-engineering the backend.

---

## What the Application Does

1. A user submits a research query (e.g. *"What are the latest advances in solid-state batteries?"*).
2. The backend creates a **research job** and returns a `job_id` immediately (HTTP 202).
3. A multi-agent LangGraph pipeline runs **asynchronously** in the background:
   - **plan** → **research** (web search via Tavily) → **evidence** → **claim_extraction** → **fact_check** → **citation** → **confidence** → **writer** → **critic**.
4. The frontend receives **live progress** over Server-Sent Events (SSE).
5. When the job completes, the frontend fetches the **final report** (with citations, sources, evidence, fact checks, and a confidence rating) via the status endpoint.
6. Completed jobs remain queryable for a configurable TTL (default 3600 s), then are cleaned up.

---

## Overall Architecture

```
┌──────────────────────────────┐        ┌─────────────────────────────────────┐
│  Frontend (Phase 2E, Next.js) │        │  Backend (FastAPI, Phase 2D done)   │
│  ┌──────────────────────────┐ │  HTTP  │  ┌───────────────────────────────┐  │
│  │ lib/api/research.ts      │◄┼────────┼──►│ backend/app/api.py           │  │
│  │ lib/sse/research-stream.ts│ │        │  │  · Pydantic models           │  │
│  └──────────────────────────┘ │        │  │  · job lifecycle (queued→    │  │
│  UI components / pages        │        │  │    running→completed|failed) │  │
│  (SSE + polling + state)      │        │  │  · SSE stream (observe-only) │  │
└──────────────────────────────┘        │  │  · CORS, X-Request-ID, TTL    │  │
                                        │  └───────────────┬───────────────┘  │
                                        │                  │ delegates to    │
                                        │  ┌───────────────▼───────────────┐  │
                                        │  │ backend/app/main.py            │  │
                                        │  │  run/arun_research_pipeline*   │  │
                                        │  └───────────────┬───────────────┘  │
                                        │                  │ invokes         │
                                        │  ┌───────────────▼───────────────┐  │
                                        │  │ backend/app/graph/graph.py     │  │
                                        │  │  compiled LangGraph StateGraph │  │
                                        │  │  plan→research→…→critic→route  │  │
                                        │  └───────────────┬───────────────┘  │
                                        │   ┌──────────────┼───────────────┐  │
                                        │   ▼              ▼               ▼  │
                                        │ agents/        rag/            tools/│
                                        │ (planner,      (ingestion,      (web │
                                        │  fact_checker,  chunking,       search,│
                                        │  writer, ...)   embeddings,     scrape)│
                                        │                 vectorstore)        │
                                        └─────────────────────────────────────┘
```

### Frontend / Backend responsibilities

| Layer | Responsibility |
|---|---|
| **Frontend** (Phase 2E) | Research input & submission, live SSE progress, report rendering, citations/evidence presentation, history, error/empty/loading states, responsive layout. Treats the backend as an **external API**. |
| **Backend** (this repo) | All research logic, job lifecycle, progress streaming, observability, error safety, CORS. UI-agnostic. |

---

## Research Pipeline Overview

The pipeline is a compiled **LangGraph StateGraph** (`backend/app/graph/graph.py`).
Topology:

```
START → plan → research → evidence → claim_extraction → fact_check
      → citation → confidence → writer → critic → [conditional router]
          ├── complete            → END
          ├── insufficient        → END
          └── additional_research → increment_rounds → research (bounded loop)
```

- **Single pass by default**: `RESEARCH_LOOP_MAX_ROUNDS=0` (loop disabled).
- The loop is bounded by `settings.research_loop_max_rounds` when enabled.
- `increment_rounds` is internal bookkeeping and is **never surfaced** as a progress step.

### Agent architecture (one agent = one node's brain)

| Agent / node | File | What it does |
|---|---|---|
| `plan` | `backend/app/agents/planner.py` | Produces research angles + whether to use RAG. |
| `research` | `backend/app/graph/nodes.py` + `backend/app/tools/web.py` | Web search via **Tavily** (direct call — zero LLM calls) + optional RAG retrieval. |
| `evidence` | `backend/app/agents/evidence.py` | Normalizes gathered material into numbered evidence items (`E1`, `E2`, …). |
| `claim_extraction` | `backend/app/agents/claim_extractor.py` | Extracts 3–5 key claims from the evidence. |
| `fact_check` | `backend/app/agents/fact_checker.py` | Batch-verifies claims (supported / unsupported / needs more research). |
| `citation` | `backend/app/agents/citation.py` | Assigns deterministic numbered citations (`[1]`, `[2]`, …). |
| `confidence` | `backend/app/agents/confidence.py` | Scores overall confidence; also decides routing after the critic. |
| `writer` | `backend/app/agents/writer.py` | Writes the final report draft (cites numbered sources). |
| `critic` | `backend/app/agents/critic.py` | Reviews the report (disabled by default: `RUN_CRITIC=false`). |

LLM calls are served by **Groq** (`llama-3.1-8b-instant`) through a
rate-limit-resilient wrapper (`backend/app/agents/llm.py`). Embeddings use
**Google Gemini**; the vector store is **Qdrant** (local embedded mode) for RAG.

---

## API Architecture

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness probe → `{"status": "ok"}`. |
| `/research` | POST | Create a job → `202 {"job_id": "...", "status": "queued"}`. |
| `/research/{job_id}` | GET | Job status + final `result` (or safe `error`). |
| `/research/{job_id}/progress` | GET | Live progress (`current_step`, `completed_steps`). |
| `/research/{job_id}/stream` | GET | Server-Sent Events progress stream. |

- OpenAPI docs at `/docs`; machine schema at `/openapi.json` (OpenAPI 3.1).
- Every response carries an **`X-Request-ID`** header (incoming value validated,
  or a generated UUID).
- **CORS** allows `http://localhost:3000` and `http://127.0.0.1:3000`
  (the Next.js dev server) — explicit origins only, credentials enabled.
- Errors: `404` unknown/expired job, `422` invalid request body, `500`
  `{"detail": "Internal server error"}` (never leaks internals).

### How a research request flows through the system

```
User enters query
   │
   ▼  POST /research {"query": "..."}
   │  202 { job_id, status: "queued" }
   ▼
Background task (_run_job):
   queued ──► running ──► (on_step per logical stage) ──► completed | failed
   │                            │                              │
   │                            ▼                              ▼
   │              GET /research/{job_id}/progress   GET /research/{job_id}
   │              GET /research/{job_id}/stream     → result { report, sources,
   │              (SSE: queued/progress/completed/     citations, confidence, … }
   │               failed events)                     or error
   ▼
Frontend renders live progress, then the final report.
```

### Job lifecycle

```
queued ──► running ──► completed   (result available via status endpoint)
                └────► failed      (safe error via status endpoint / SSE failed event)
```

- Terminal jobs are deleted after `JOB_TTL_SECONDS` (default 3600 s). After
  expiry they behave exactly like unknown jobs → **404**.
- Jobs live **in memory** (by design); jobs are lost on backend restart.

### SSE architecture (for the frontend)

- `GET /research/{job_id}/stream` returns `text/event-stream`.
- Events: **queued**, **progress**, **completed**, **failed** — each is
  `event: <name>` + a JSON `data` block.
- `data` payload shape = the progress payload (`job_id`, `status`,
  `current_step`, `completed_steps`); the `failed` event also adds `error`.
- **`completed`/`failed` are terminal** — the stream closes right after.
- **SSE never duplicates the final report.** After `completed`, fetch
  `GET /research/{job_id}` for the full result.
- On (re)connect the **current state is replayed** (first event may be
  `progress` or `completed`, not necessarily `queued`). The frontend must
  treat every event as a state snapshot and reconnect safely **without**
  starting a new research job.

---

## Important Folders

| Folder | Purpose |
|---|---|
| `backend/` | Entire backend package (FastAPI + pipeline + RAG). |
| `backend/app/` | Application code. |
| `backend/app/api.py` | **The HTTP API** — endpoints, models, job store, SSE, middleware. The primary file the frontend talks to. |
| `backend/app/main.py` | Pipeline entry points (`run_*`, `arun_*`) + result mapping. |
| `backend/app/graph/` | LangGraph state, nodes, and compiled graph. |
| `backend/app/agents/` | Individual agent brains (planner, fact_checker, writer, …) + LLM wrapper. |
| `backend/app/rag/` | RAG: ingestion, cleaning, chunking, embeddings, vector store. |
| `backend/app/tools/` | Web tools: Tavily `web_search`, `scrape_url`, URL utilities. |
| `backend/app/core/` | Configuration (`config.py`, pydantic-settings). |
| `backend/tests/` | Offline pytest suite (447 tests). |
| `app.py` | Legacy Streamlit prototype UI (keep — do not use for the new frontend). |
| `frontend/` | **Does not exist yet** — created in Phase 2E by Antigravity. |
| `.venv/` | Python virtual environment (never touch). |

Full detail: see `FOLDER_GUIDE.md`.

---

## Frontend Responsibilities (Phase 2E)

- Research input + submission (POST `/research`).
- Live progress via SSE (`/research/{job_id}/stream`).
- Job states: `queued`, `running`, `completed`, `failed`.
- Final report rendering (markdown), citations, sources, evidence, fact checks.
- Research history (in-browser — the backend has **no history endpoint yet**).
- Loading / error / empty / success states everywhere.
- Responsive desktop + mobile.
- A clean, isolated API layer (`lib/api/*`, `lib/sse/*`).

See `FRONTEND_UI_SPEC.md`, `UI_PAGES.md`, `COMPONENT_MAP.md`.

---

## API Endpoints (summary — full reference in `API_FOR_FRONTEND.md`)

- `GET /health` → `{"status": "ok"}`
- `POST /research` → `202 {"job_id": string, "status": "queued"}`
- `GET /research/{job_id}` → `{"job_id", "status", "result"?|"error"?}`
  (statuses: `queued | running | completed | failed`)
- `GET /research/{job_id}/progress` → `{"job_id", "status", "current_step", "completed_steps"}`
- `GET /research/{job_id}/stream` → SSE (`queued | progress | completed | failed`)

---

## Expected Frontend States

```
IDLE ──► SUBMITTING ──► QUEUED ──► RUNNING ──► COMPLETED
                              │                 │
                              └──► FAILED ◄─────┘
```

- `IDLE` — no job yet (landing state).
- `SUBMITTING` — POST in flight.
- `QUEUED` — job created, worker not started (SSE `queued`).
- `RUNNING` — worker active (SSE `progress`; `current_step` / `completed_steps` update).
- `COMPLETED` — fetch result via status endpoint (SSE `completed`).
- `FAILED` — show safe error, allow retry (SSE `failed`).

**Never assume a fixed number of steps.** The contract exposes
`current_step` and `completed_steps` as an ordered, open-ended list; stages may
repeat if the research loop is ever enabled. Progress UI must render an
arbitrary sequence.

---

## Design Requirements (summary — full spec in `FRONTEND_UI_SPEC.md`)

- Professional **research workstation**, premium SaaS, technical but approachable.
- **NOT** a ChatGPT/Claude clone, generic chatbot, or generic admin dashboard.
- Strong visual hierarchy, consistent spacing, polished typography.
- Subtle animations, skeleton loaders, meaningful loading states.
- Accessible, keyboard-friendly, responsive.
- Honor the existing design DNA from the Streamlit prototype
  (dark `#0a0a0f` canvas, warm amber accent `#ff8c32`, Syne / DM Sans / DM Mono
  typography, instrument-like precision) unless reference screenshots clearly
  override it.
- Avoid: excessive gradients/glassmorphism, giant hero sections, chatbot-style
  single-column chat, meaningless animation, generic AI purple/blue gradients.

---

## Development Workflow

1. Backend already runs standalone:
   ```bash
   cd "d:/Multi Agent System"
   .venv/Scripts/python.exe -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000
   ```
2. OpenAPI: http://127.0.0.1:8000/docs
3. Tests (offline, no external services):
   ```bash
   .venv/Scripts/python.exe -m pytest -q          # 447 passing, 0 warnings
   ```
4. The frontend (Phase 2E) will run separately (e.g. `next dev` on port 3000)
   and talk to `http://127.0.0.1:8000` — CORS already allows it.
5. **Never run a real research request just to test the UI** — external API
   quota is unnecessary; use a mocked/offline pipeline or fixture data.

---

## Rules for Future AI Coding Agents

1. **Do not redesign the backend.** It is Phase 2D complete and intentionally
   thin/observable. No auth, no PostgreSQL, no new backend features unless a
   future phase explicitly requires them.
2. **Do not modify:** LangGraph topology, agents, prompts, RAG, pipeline
   behavior, API response bodies, SSE event format, error handling, CORS,
   request IDs, TTL cleanup, or the Streamlit `app.py`.
3. **Preserve every API response body and SSE event format.**
4. **Frontend treats the backend as an external API** — isolated API layer,
   no scattered `fetch()` calls.
5. **No unnecessary dependencies.** Use the selected frontend stack
   (Next.js + TypeScript + Tailwind + shadcn/ui) and reuse components.
6. **All backend tests must stay green** (`pytest -q`). Backend changes should
   come with offline tests.
7. **Do not hardcode external-service behavior** in tests or fixtures.
8. When in doubt, re-read `API_FOR_FRONTEND.md` before touching any fetch/SSE
   code.

---

## FRONTEND UI HANDOFF FOR ANTIGRAVITY

> This package exists so a frontend-coding agent (Antigravity) can build the
> Phase 2E UI **without reverse-engineering the backend**.

### What Antigravity must know

1. **The backend is an external API.** All communication goes through
   `http://127.0.0.1:8000` (dev). Build a clean API layer — e.g.
   `frontend/lib/api/research.ts`, `frontend/lib/api/health.ts`, and an
   isolated SSE module `frontend/lib/sse/research-stream.ts`. Never scatter
   `fetch()` calls through components.
2. **The job model.** Submit → get `job_id` → poll `GET /research/{job_id}`
   and/or subscribe to `GET /research/{job_id}/stream`. Statuses:
   `queued`, `running`, `completed`, `failed`.
3. **SSE is the live-progress channel.** Events: `queued`, `progress`,
   `completed`, `failed`. Terminal events close the stream. **The final
   report is NOT in SSE** — after `completed`, call
   `GET /research/{job_id}` to get `result`.
4. **SSE reconnection.** Reconnecting replays the current state. The frontend
   must reconnect safely and **never** POST a new research job when the SSE
   connection drops — only reconnect the stream.
5. **Do not assume a fixed step list.** Render progress from
   `current_step` + `completed_steps` (open-ended, ordered; may repeat).
6. **No history backend exists yet.** Research history must be maintained
   client-side (localStorage) in Phase 2E.
7. **Design direction.** Read `FRONTEND_UI_SPEC.md` and honor the existing
   design DNA + reference screenshots. Do **not** produce a generic AI
   dashboard or chatbot clone.
8. **Read order (mandatory before coding):**
   1. `README.md` (this file)
   2. `FRONTEND_UI_SPEC.md`
   3. `UI_PAGES.md`
   4. `API_FOR_FRONTEND.md`
   5. `FOLDER_GUIDE.md`
   6. `COMPONENT_MAP.md`
   7. `ANTIGRAVITY_PROMPT.md`
9. **Do not start by coding.** Inspect the repo, read all docs, study the
   reference screenshots, extract visual patterns, write a UI implementation
   plan, identify reusable components and page layouts — then implement.

### The 7 documents in this package

| File | What it is for |
|---|---|
| `README.md` | This overview — architecture, flows, rules. |
| `FRONTEND_UI_SPEC.md` | The visual/UX specification (most important design doc). |
| `UI_PAGES.md` | Every page: purpose, route, layout, sections, components, data, API, states. |
| `API_FOR_FRONTEND.md` | Frontend-focused API + SSE contract reference. |
| `FOLDER_GUIDE.md` | Repository map — what to touch, what never to touch. |
| `COMPONENT_MAP.md` | Reusable component inventory grouped by domain. |
| `ANTIGRAVITY_PROMPT.md` | A copy-paste prompt that boots Antigravity into this task. |
