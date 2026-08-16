# InsightForge — Frontend

The Phase 2E frontend for the InsightForge multi-agent research workstation.
Next.js (App Router) + TypeScript + Tailwind CSS v4.

> **Status: visual foundation (mock data).** This stage uses realistic mock
> data and local UI state. Real FastAPI integration (POST `/research`, SSE,
> etc.) is the next stage — the API/SSE layer is already scaffolded in
> `lib/api` and `lib/sse` with typed contracts in `lib/types/api.ts`.

## Getting started

```bash
npm install
npm run dev        # http://localhost:3000
npm run lint       # eslint (must be clean)
npm run build      # production build
npm run start      # serve the production build
```

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

The FastAPI backend lives at `../backend` and is **read-only** for this task.
See the API contract in `lib/types/api.ts` and the handoff docs at the repo
root (`API_FOR_FRONTEND.md`). When the next stage wires real integration,
swap the mock stubs in `lib/api/*` and `lib/sse/*` for the real calls (the
intended implementations are documented as comments in those files).
