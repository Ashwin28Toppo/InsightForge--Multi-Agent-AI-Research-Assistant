# InsightForge â€” Frontend

Next.js (App Router) + TypeScript + Tailwind CSS v4 frontend for the InsightForge research assistant.

Communicates with the FastAPI backend over HTTP and Server-Sent Events (SSE) for live research progress.

## Getting Started

1. Start the FastAPI backend (see the repo root README):
   ```bash
   cd ..   # repo root
   .venv/Scripts/python.exe -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000
   ```

2. Install dependencies and start the dev server:
   ```bash
   npm install
   npm run dev        # http://localhost:3000
   npm run lint       # eslint (must be clean)
   npm run build      # production build
   npm run start      # serve the production build
   ```

   Copy `frontend/.env.example` to `.env.local` to override the backend base URL (`NEXT_PUBLIC_API_BASE_URL`, defaults to `http://127.0.0.1:8000`).

## Routes

| Route | Page |
|---|---|
| `/` | Landing â€” research composer, pipeline overview, recent inquiries |
| `/research/[jobId]` | Research workspace â€” live progress, report, and error states |
| `/history` | Research history (localStorage) |
| `/history/[jobId]` | Archived snapshot detail |

## Project Structure

```
app/                    # App Router pages (home, research workspace, history)
components/
  layout/               # AppShell, Sidebar, BottomTabBar, TraceabilityRail
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
  api/                  # Fetch wrapper + typed API functions
  sse/                  # Isolated SSE client (EventSource + exponential backoff)
  types/api.ts          # API + SSE TypeScript contracts (mirrors backend)
  constants/pipeline.ts # Static pipeline stage labels/descriptions
  history/store.ts      # localStorage research history
  utils/url.ts          # Domain extraction utilities
hooks/                  # useHealth, useResearchJob, useResearchStream
```

## Design System

- Color palette: graphite/charcoal, muted indigo/blue/cyan.
- Design tokens centralized in `app/globals.css` (`@theme`) â€” do not use hardcoded colors.
- Typography: Syne (display), DM Sans (body), DM Mono (technical metadata).

## Backend Integration

The FastAPI backend lives at `../backend`. The API contract is typed in `lib/types/api.ts`.

Key integration points:

| File | Purpose |
|---|---|
| `lib/api/client.ts` | Shared fetch wrapper â€” base URL, JSON, `X-Request-ID`, typed `ApiError` |
| `lib/api/research.ts` / `lib/api/health.ts` | Typed endpoint functions |
| `lib/sse/research-stream.ts` | Native `EventSource` client with exponential backoff reconnection; never creates a new job on reconnect |
| `hooks/useResearchStream.ts` | SSE + polling fallback (polling only when stream is not open); stops at terminal states or 404 |
| `hooks/useResearchJob.ts` | Status/result fetch with `refresh()`; result normalized by `lib/utils/normalize.ts` |
| `lib/history/store.ts` | localStorage history â€” written on job completion, read by `/history` and the home page |
