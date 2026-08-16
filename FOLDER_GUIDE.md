# InsightForge — Repository Folder Guide

**For Antigravity (Phase 2E frontend agent).** A map of the actual repository
structure — what lives where, what matters to a frontend agent, and what must
**never** be modified.

> Actual top-level layout:
> ```
> d:\Multi Agent System\
> ├── backend/            ← the entire backend (FastAPI + pipeline + RAG)
> ├── app.py              ← legacy Streamlit prototype UI (do NOT touch)
> ├── conftest.py         ← pytest root config
> ├── requirements.txt    ← backend Python dependencies
> ├── .env / .env.example ← environment config (keys, CORS, TTL, tokens)
> ├── .venv/              ← Python virtual environment (never touch)
> └── frontend/           ← DOES NOT EXIST YET — created in Phase 2E
> ```

---

## `backend/` — the backend package (READ-ONLY for the frontend agent)

The whole backend is **out of scope** for the frontend task. Read it to
understand contracts; never modify it.

| Path | Purpose |
|---|---|
| `backend/app/api.py` | ⭐ **The HTTP API.** Endpoints, Pydantic models, job store, SSE, CORS, request IDs, TTL cleanup. This is what the frontend integrates with. **Read this file.** |
| `backend/app/main.py` | Pipeline entry points (`run_research_pipeline`, `arun_research_pipeline`, `arun_research_pipeline_streaming`) + `_to_application_result` (defines the result contract). Read to understand `result` fields. |
| `backend/app/graph/` | LangGraph: `state.py` (typed state), `nodes.py`, `graph.py` (topology). Explains the 9 logical stages. Read-only. |
| `backend/app/agents/` | Agent brains: `planner.py`, `evidence.py`, `claim_extractor.py`, `fact_checker.py`, `citation.py`, `confidence.py`, `writer.py`, `critic.py`, `llm.py`. Read to understand stage names/output shapes. Read-only. |
| `backend/app/rag/` | RAG subsystem: `ingestion.py`, `cleaning.py`, `chunking.py`, `embeddings.py`, `vectorstore.py`, `schemas.py`. Read-only. |
| `backend/app/tools/` | `web.py` — Tavily `web_search`, `scrape_url`, URL utils. Read-only. |
| `backend/app/core/` | `config.py` — pydantic-settings (env + `.env`). Explains CORS origins, TTL, token budgets, loop control. Read-only. |
| `backend/tests/` | Offline pytest suite (447 tests). Never modify; never run real external calls. `test_api.py` documents expected API behavior. |

### Frontend agent's relationship with `backend/`

- **Read** `api.py`, `main.py`, `graph/state.py` to confirm contracts.
- **Never modify** any backend file.
- **Never run** a real research request to "test" — use a mocked/offline
  pipeline or fixture data (external quota is unnecessary).

---

## `app.py` — legacy Streamlit prototype (READ-ONLY)

The current single-file UI. It contains **design DNA** (dark canvas, amber
accent, Syne/DM Sans/DM Mono typography) worth referencing for visual
direction — see `FRONTEND_UI_SPEC.md § D`. Do **not** modify it; do **not**
build the new frontend on Streamlit.

---

## `conftest.py` — pytest root config (READ-ONLY)

Makes `backend` importable for the offline test suite. Not relevant to the
frontend.

---

## `requirements.txt` — backend dependencies (READ-ONLY)

Python deps only (FastAPI, uvicorn, LangChain/LangGraph, Groq, Gemini, Tavily,
Qdrant, Streamlit, pytest). **Do not add frontend deps here** — the frontend
has its own package manifest.

---

## `.env` / `.env.example` — configuration (READ-ONLY)

Backend runtime config: API keys, `CORS_ORIGINS` (already includes the Next.js
dev origins), `JOB_TTL_SECONDS`, token budgets, Qdrant, etc. Frontend agents
**must not** touch these files or commit secrets. The frontend gets its own
`NEXT_PUBLIC_API_BASE_URL` (see `API_FOR_FRONTEND.md`).

---

## `.venv/` — Python virtual environment (NEVER TOUCH)

Backend interpreter + packages. Never modify, never delete, never install
frontend packages here.

---

## `frontend/` — Phase 2E target (created by Antigravity)

Does not exist yet. Recommended structure (subject to the chosen stack —
Next.js + TypeScript + Tailwind + shadcn/ui):

```
frontend/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # AppShell (sidebar + header) wrapper
│   ├── page.tsx                # Landing / home
│   ├── research/[jobId]/page.tsx   # Workspace (running) + report (completed)
│   ├── history/page.tsx        # History list
│   ├── history/[jobId]/page.tsx    # History detail
│   ├── not-found.tsx
│   ├── error.tsx
│   └── globals.css             # design tokens (CSS variables / Tailwind theme)
├── components/                 # all UI components (see COMPONENT_MAP.md)
│   ├── layout/
│   ├── research/
│   ├── progress/
│   ├── report/
│   ├── evidence/
│   ├── citations/
│   ├── history/
│   ├── feedback/
│   └── ui/                     # shadcn/ui primitives
├── lib/
│   ├── api/
│   │   ├── client.ts           # fetch wrapper (base URL, JSON, errors)
│   │   ├── research.ts         # submitResearch / getJobStatus / getJobProgress
│   │   └── health.ts           # getHealth
│   ├── sse/
│   │   └── research-stream.ts  # subscribeResearchStream (isolated SSE)
│   ├── types/
│   │   └── api.ts              # all API + SSE types
│   ├── state/
│   │   └── research-store.ts   # useResearchJob / useResearchStream hooks
│   └── history/                # localStorage history helpers
├── hooks/
│   ├── useResearchJob.ts
│   └── useResearchStream.ts
├── styles/
├── package.json
├── tailwind.config.*
├── tsconfig.json
└── .env.local                  # NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

### Dependency relationships (frontend → backend)

- `lib/api/*` → `backend/app/api.py` endpoints (HTTP).
- `lib/sse/research-stream.ts` → `GET /research/{job_id}/stream` (SSE).
- `lib/types/api.ts` → mirrors the Pydantic models in `backend/app/api.py`.
- UI components → hooks → `lib/api` / `lib/sse` (never direct `fetch`).

---

## DO NOT MODIFY (frontend agent)

- `backend/` — every file (especially `api.py`, `main.py`, `graph/`,
  `agents/`, `rag/`, `tools/`, `core/`, `tests/`).
- `app.py` (Streamlit prototype).
- `conftest.py`, `requirements.txt`.
- `.env`, `.env.example`.
- `.venv/`, `.git/`, `.gitignore`.
