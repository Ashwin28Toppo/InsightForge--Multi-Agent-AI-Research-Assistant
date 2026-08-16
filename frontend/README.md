# InsightForge — Frontend

The Phase 2E frontend for the InsightForge multi-agent research workstation.
Next.js (App Router) + TypeScript + Tailwind CSS v4.

> **Status: real FastAPI integration.** The frontend talks to the FastAPI
> backend over HTTP (`POST /research`, status, progress) and Server-Sent
> Events (`/research/{job_id}/stream`) with reconnection + a polling fallback.
> Completed research is archived to localStorage. Mock data in `lib/mock`
> remains available but is **not** used by the default app paths.

## Getting started

1. Start the FastAPI backend (see the repo root README):
   ```bash
   cd ..   # repo root
   .venv/Scripts/python.exe -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000
   ```
2. Frontend (backend base URL via `NEXT_PUBLIC_API_BASE_URL`, defaults to
   `http://127.0.0.1:8000`):
   ```bash
   npm install
   npm run dev        # http://localhost:3000
   npm run lint       # eslint (must be clean)
   npm run build      # production build
   npm run start      # serve the production build
   ```
   Copy `frontend/.env.example` to `.env.local` to override the base URL.

## Routes

| Route | Page |
|---|---|
| `/` | Landing — composer, pipeline overview, recent inquiries |
| `/research/[jobId]` | Research workspace — live progress / report / failed states |
| `/history` | Research history (localStorage, mock-seeded) |
| `/history/[jobId]` | Archived snapshot detail |

## Structure

```
app/                    # App Router pages (home, research workspace, history)
components/
  layout/               # AppShell, Sidebar-in-AppShell, BottomTabBar, TraceabilityRail
  progress/             # ProgressTimeline (dynamic stage array)
  report/               # ReportViewer + MarkdownRenderer
  evidence/             # EvidencePanel / EvidenceCard
  citations/            # CitationPanel / CitationCard
  claims/               # FactCheckList / VerdictBadge
  ui/                   # StatusBadge, ConfidenceBadge
  feedback/             # EmptyState, Skeleton
  history/              # HistoryItem
  research/             # ResearchComposer
lib/
  api/                  # fetch wrapper + typed API functions (mock stubs now)
  sse/                  # isolated SSE client (mock now)
  types/api.ts          # API + SSE TypeScript contracts (mirror backend)
  mock/research.ts      # realistic mock research data + runMockResearch
  history/store.ts      # localStorage history
  utils/url.ts          # domain extraction
hooks/                  # useHealth, useResearchJob, useResearchStream
```

## Design system

- Cool professional palette (graphite/charcoal, muted indigo/blue/cyan) —
  the legacy orange/amber identity is intentionally **not** used.
- Design tokens centralized in `app/globals.css` (`@theme`) — do not scatter
  hardcoded colors.
- Typography: Syne (display), DM Sans (body), DM Mono (technical metadata).

## Backend

The FastAPI backend lives at `../backend` and is **read-only** for frontend
work. See the API contract in `lib/types/api.ts` and the handoff docs at the
repo root (`API_FOR_FRONTEND.md`).

### Integration notes

- `lib/api/client.ts` — shared fetch wrapper (base URL, JSON, `X-Request-ID`,
  typed `ApiError` exposing the server request id).
- `lib/api/research.ts` / `lib/api/health.ts` — typed endpoint functions.
- `lib/sse/research-stream.ts` — native `EventSource` client with exponential
  backoff reconnection (never creates a new job), terminal-event handling,
  and a max-attempt cap that falls back to polling.
- `hooks/useResearchStream.ts` — SSE + progress-poll fallback (polling only
  when the stream is not open), stops at terminal/404.
- `hooks/useResearchJob.ts` — status/result fetch + `refresh()`; result is
  normalized by `lib/utils/normalize.ts` (defensive, never crashes on missing
  fields).
- History: `lib/history/store.ts` (localStorage) is written on completion and
  read by `/history`, `/history/[jobId]`, and the home page.
