# InsightForge — UI Pages

**For Antigravity (Phase 2E frontend agent).** Every page the frontend should
ship, with purpose, route, layout, sections, components, data, API endpoints,
and the loading/error/empty/responsive/navigation behavior.

> **Constraint:** only build against functionality that exists on the backend.
> There is **no history endpoint** and **no auth** — history is client-side
> (localStorage) for Phase 2E. Do not invent backend features.

Recommended routes use the Next.js App Router:
`frontend/app/<route>/page.tsx`.

---

## Page index

| # | Page | Suggested route |
|---|---|---|
| 1 | Landing / Home | `/` |
| 2 | Research workspace (active) | `/research/[jobId]` (state = running) |
| 3 | Research report / result | `/research/[jobId]` (state = completed) |
| 4 | Evidence & citations view | `/research/[jobId]?tab=evidence` (in-workspace) |
| 5 | History | `/history` |
| 6 | History detail | `/history/[jobId]` (replays a saved result) |
| 7 | Error states | inline + full-page (no dedicated route needed) |
| 8 | Empty states | inline (no dedicated route needed) |
| 9 | 404 / not found | `not-found.tsx` (App Router) |

---

## 1. Landing / Home page — `/`

**Purpose**: First-run experience. Sell the *capability* (multi-agent
research) without a chatbox-only page. Primary action: start research.

**Layout**: App shell (sidebar + header) with a hero region. NOT a giant
centered chat input. A left-aligned or split hero: product statement on the
left, research composer on the right. Below: a compact "how it works" strip
(the 9 stages as a static mini-timeline) and recent history (from
localStorage).

**Major sections**:
- Header (identity + backend health chip).
- Hero: eyebrow ("Multi-agent research assistant"), H1, one-line value prop.
- Research composer (query input + submit) — prominent, focused.
- "How InsightForge works": static stage strip (plan → research → evidence →
  claim_extraction → fact_check → citation → confidence → writer → critic).
- Recent research (from local history) — optional, if history exists.

**Components**: `AppShell`, `Header`, `HealthBadge`, `ResearchComposer`,
`StageStrip` (static), `HistoryList` (recent, compact), `EmptyState`.

**Data required**: none from API on load (health optional). Local history for
the recent list.

**API endpoints**: `GET /health` (optional status chip).

**Loading state**: skeleton for the recent-history block only.

**Error state**: if `/health` fails → "Backend offline" chip (non-blocking);
composer still usable (submit will surface the error inline).

**Empty state**: no history → the composer is the hero; a subtle "No research
yet — start with a question" hint.

**Responsive**: hero stacks to one column < 768 px; composer full-width.

**Navigation**: submit → navigate to `/research/[jobId]`; history item →
`/history/[jobId]`.

---

## 2. Research workspace — `/research/[jobId]` (active / running)

**Purpose**: Show the live research in progress. This is the "bridge" screen
between submit and report.

**Layout**: App shell. Left/main region = progress; right rail = sources-so-far
(live evidence/sources). Header shows the query + job status.

**Major sections**:
- Header: query (editable-locked), status badge (`queued` / `running`), job ID
  (mono, truncated), elapsed time.
- **Progress timeline**: the 9 logical stages as a vertical/horizontal
  timeline; completed stages checked, current stage pulsing, pending stages
  dimmed. Driven by `current_step` + `completed_steps` (open-ended — stages
  may repeat if the loop is enabled; render repeats as a second pass).
- Stage activity indicator: "Agent: fact_check" mono label + spinner.
- Right rail: sources/evidence discovered so far (live updates).
- Actions: "Cancel" is NOT a backend feature — do not offer backend cancel.
  Offer "Copy query" and "Go to report when done".

**Components**: `ProgressHeader`, `StatusBadge`, `ProgressTimeline`,
`StageItem`, `AgentActivityIndicator`, `EvidencePanel` (live), `Skeleton`.

**Data required**: `job_id`, SSE events (`queued`/`progress`), progress from
`GET /research/{job_id}/progress` (initial + fallback), evidence/sources
(only what arrives via events or a completed fetch).

**API endpoints**: `GET /research/{job_id}/stream` (SSE, primary),
`GET /research/{job_id}/progress` (fallback/poll while SSE reconnects).

**Loading state**: skeleton timeline until first SSE event or initial poll.

**Error state**: SSE disconnected → inline "Reconnecting…" banner (reconnect
loop, no new POST). Polling fails → inline error + retry.

**Empty state**: no events yet → "Worker starting…" stage strip with `queued`.

**Responsive**: rail becomes a slide-over panel / bottom sheet on mobile.

**Navigation**: on `completed` → auto-transition to report state (same route);
back → history/list.

---

## 3. Research report / result — `/research/[jobId]` (completed)

**Purpose**: Read the final report with full traceability.

**Layout**: App shell. Main region = the report (markdown). Right rail =
tabs/stacked panels: **Sources**, **Evidence**, **Citations**, **Fact
checks**. Header = query + `completed` badge + confidence + duration.

**Major sections**:
- Header meta: query, `completed` status, confidence badge (`high`/`medium`/
  `low`/unknown), time taken, job ID, "Copy", "New research".
- Report body: rendered markdown (headings, lists, tables). Inline citation
  markers `[1]`, `[2]` link to the citation panel.
- Meta strip: sources count, citations count, fact-check summary.
- Right rail (tabs or stacked accordions):
  - **Sources** — list of URLs with titles (from `result.sources`).
  - **Evidence** — evidence items (id, type web/rag, snippet, source).
  - **Citations** — numbered citation cards (`index`, `title`, `url`).
  - **Fact checks** — claims + verdicts (`supported` / `unsupported` /
    `needs more research`) + confidence.
- Footer actions: "New research", "Save to history" (client-side).

**Components**: `ReportViewer`, `MarkdownRenderer`, `CitationRef`,
`ConfidenceBadge`, `ReportMeta`, `EvidencePanel`, `CitationPanel`,
`SourceList`, `FactCheckList`, `StatusBadge`, `CopyButton`.

**Data required**: `GET /research/{job_id}` → `result`:
`report` (markdown), `sources` (string[]), `citations` (object[]),
`confidence` (string), `critic_feedback`, `critic_score`, `evidence`
(object[]), `fact_checks` (object[]), `claims` (string[]), `errors` (string[]).
All fields are best-effort — render defensively (fields may be absent).

**API endpoints**: `GET /research/{job_id}`.

**Loading state**: report skeleton (heading + paragraph shimmer).

**Error state**: 404 (job expired) → full "Research expired" state + "Start
new research". Network → inline retry. `result.errors` non-empty → warning
banner listing safe errors.

**Empty state**: `result` present but `report` empty → explain pipeline
returned no report; show sources/evidence if any.

**Responsive**: rail → tabs on mobile; markdown reflows.

**Navigation**: citation refs scroll to citation panel; "New research" →
`/`; history save → toast.

---

## 4. Evidence & citations view — `/research/[jobId]?tab=evidence`

**Purpose**: Deep-dive into the traceability of a completed report.

**Layout**: Same as report page but the right rail is the primary focus, or a
dedicated tabbed view (Report | Sources | Evidence | Citations | Fact checks).

**Major sections**:
- Tab bar (Report / Sources / Evidence / Citations / Fact checks).
- Evidence tab: evidence cards (E1…En) with type badge (`web`/`rag`), text
  snippet, source link, page/chunk metadata.
- Citations tab: numbered citation cards; clicking a citation shows the
  linked evidence/source.
- Fact checks tab: claims with verdict badges + confidence bars.

**Components**: `TabBar`, `EvidenceCard`, `CitationCard`, `FactCheckItem`,
`VerdictBadge`, `SourceChip`, `EvidencePanel`, `CitationPanel`.

**Data required**: same `result` payload as the report page (client-side tab
filtering; no separate API).

**API endpoints**: `GET /research/{job_id}`.

**Loading / error / empty states**: same as report page; empty evidence →
"Pipeline found no discrete evidence items" (valid edge case).

**Responsive**: tabs scroll horizontally on mobile; cards stack.

**Navigation**: tab switches; citation ↔ evidence cross-links.

---

## 5. Research history — `/history`

**Purpose**: Browse past research (client-side in Phase 2E — no backend
history API).

**Layout**: App shell. Main = list of history items (most recent first).

**Major sections**:
- Header: "Research history" + count.
- Filter/search (client-side): by query text, status, date.
- History list: item = query, status, date/time, confidence (if completed),
  snippet of report, duration.
- Item actions: open, copy query, delete (local).

**Components**: `HistoryList`, `HistoryItem`, `HistoryEmptyState`,
`SearchField`, `StatusBadge`, `Skeleton`.

**Data required**: localStorage records — store on completion:
`{ jobId, query, status, completedAt, confidence, reportSnippet }`. Note:
the full result can be re-fetched via `GET /research/{job_id}` if still
within TTL; otherwise history shows the saved snapshot.

**API endpoints**: none required on load; optional re-fetch per item.

**Loading state**: skeleton rows.

**Error state**: localStorage unavailable → inline notice; items degrade to
snapshot-only.

**Empty state**: `HistoryEmptyState` → "No research yet" + CTA.

**Responsive**: single column; swipe/delete on mobile optional.

**Navigation**: item → `/history/[jobId]`; "New research" → `/`.

---

## 6. Individual history / research detail — `/history/[jobId]`

**Purpose**: Reopen a past result (from local snapshot; re-fetch live result
if still available).

**Layout**: App shell. Same layout as the report page (report + rail).

**Major sections**: header (query, date, status, confidence) + report body +
evidence/citations panels (from the saved snapshot or re-fetched result).

**Components**: `ReportViewer`, `HistoryItem`, `EvidencePanel`,
`CitationPanel`, `StatusBadge`, `BackButton`.

**Data required**: local snapshot; optionally `GET /research/{job_id}` to
refresh (returns 404 if the job expired/TTL-cleaned → fall back to snapshot
with an "archived snapshot" note).

**API endpoints**: `GET /research/{job_id}` (best-effort refresh).

**Loading state**: skeleton while reading local + (optional) re-fetch.

**Error state**: 404 → show snapshot + note "Original job expired — showing
saved snapshot."

**Empty state**: unknown id in local history → `EmptyState` + link to history.

**Responsive**: as report page.

**Navigation**: back → `/history`; "New research" → `/`.

---

## 7. Error states

Full-page (unrecoverable) and inline (recoverable) variants:

- **Backend unreachable**: full-page state — "Can't reach the research
  service" + "Retry" (re-checks `/health`). Inline variant as a header chip.
- **Job failed**: workspace shows `failed` status + safe `error` message +
  "Try again" (new job, new query) — never a raw traceback.
- **Validation (422)**: inline under the query field ("Query can't be empty").
- **404 job not found / expired**: full-page "Research not found or expired"
  + "Start new research".
- **Unexpected (500)**: generic "Something went wrong" + retry; the safe
  `{"detail": "Internal server error"}` is the only body to show.

**Components**: `FullPageError`, `InlineError`, `ErrorBoundaryState`,
`Toast`, `RetryButton`.

**Routes**: App Router `error.tsx` (nearest) + `not-found.tsx`.

---

## 8. Empty states

Inline empty states per container (history, sources, evidence, citations,
fact checks) + the landing empty state. Each: title, one-line explanation,
primary action. See `FRONTEND_UI_SPEC.md § C — Empty states`.

**Components**: `EmptyState` (tone prop: `info` | `muted`).

---

## 9. 404 page — App Router `not-found.tsx`

**Purpose**: Unknown route.

**Layout**: App shell; centered-but-small: product mark, "Page not found",
link to `/`. No giant hero, no dead-end.

**Components**: `EmptyState`, `Button` (link to `/`).

**Responsive**: single column, vertically centered.

---

## Cross-page behaviors

- **Global shell** persists across `/`, `/research/*`, `/history*`.
- **Live transition**: submitting → workspace; workspace running →
  completed (same URL, state-driven UI); completed → report.
- **SSE reconnect** happens inside the workspace page — never triggers a new
  POST.
- **Keyboard**: `/` focuses research input on landing; `Esc` closes panels.
- **History** is written on completion (and on failure with status) to
  localStorage.
