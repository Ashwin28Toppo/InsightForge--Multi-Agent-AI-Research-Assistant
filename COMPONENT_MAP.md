# InsightForge — Frontend Component Map

**For Antigravity (Phase 2E frontend agent).** The reusable component
inventory, grouped by domain. Every component specifies its purpose, props,
data, state, interactions, and API dependency.

> **Rules:** components are **presentational** — they receive data via props
> and never call the API. All data fetching lives in hooks and `lib/api` /
> `lib/sse`. Components are typed (TypeScript), keyboard-accessible, and
> responsive. Where a component maps to a shadcn/ui primitive, extend that
> primitive with the design tokens from `FRONTEND_UI_SPEC.md`.

---

## Layout

### `AppShell`
- **Purpose**: Persistent app frame: sidebar + header + main content + optional right rail + mobile nav.
- **Props**: `{ children, sidebar?: ReactNode, header?: ReactNode, rail?: ReactNode }`.
- **Data**: none (composition only).
- **State**: sidebar collapsed/open (desktop), mobile nav open, rail open.
- **Interactions**: toggles; responsive breakpoints.
- **API**: none.

### `Sidebar`
- **Purpose**: Primary navigation rail (New Research, History, (future) Knowledge Base).
- **Props**: `{ items, active, collapsed, onNavigate }`.
- **API**: none.

### `Header`
- **Purpose**: Top bar: product identity, backend health chip, current job status (when on a job), primary actions.
- **Props**: `{ title?, health?: "online"|"offline"|"checking", jobStatus?: JobStatus, actions? }`.
- **API**: `GET /health` via a hook (or parent passes `health`).

### `MainContent`
- **Purpose**: Scrollable content region with consistent gutters.
- **Props**: `{ children }`.

### `RightRail`
- **Purpose**: Secondary panel (sources/evidence/citations/fact checks) — fixed on desktop, slide-over on mobile.
- **Props**: `{ open, onClose, children }`.

### `BottomTabBar` (mobile)
- **Purpose**: Mobile navigation (New Research, History).
- **Props**: `{ items, active, onNavigate }`.

---

## Navigation

### `SidebarNav`
- **Purpose**: Sidebar link group (label + icon + count).
- **Props**: `{ items: { key, label, icon, href, count? }[], active, onNavigate }`.

### `HistoryNav`
- **Purpose**: Jump from workspace to history and back.
- **Props**: `{ jobId?, onNewResearch }`.

### `Breadcrumb`
- **Purpose**: Page hierarchy (e.g. History / Query title).
- **Props**: `{ crumbs: { label, href? }[] }`.

### `TabBar`
- **Purpose**: In-workspace tabs: Report | Sources | Evidence | Citations | Fact checks.
- **Props**: `{ tabs, active, onChange }`.

### `BackButton`
- **Purpose**: Return to previous page.
- **Props**: `{ label?, onClick }`.

---

## Research

### `ResearchComposer`
- **Purpose**: Hero research input: textarea + submit + status microcopy.
- **Props**: `{ onSubmit(q: string), state: "idle"|"submitting", error?: string, disabled? }`.
- **Data**: none.
- **State**: local text value; external `submitting`.
- **Interactions**: Enter submits (Shift+Enter newline); `/` focuses; submit disabled while `submitting`.
- **API**: calls `submitResearch` via parent/hook (never directly).

### `ResearchInput`
- **Purpose**: The query textarea primitive.
- **Props**: `{ value, onChange, placeholder, error?, disabled? }`.

### `SubmitButton`
- **Purpose**: Primary submit action with loading state.
- **Props**: `{ loading, disabled?, label? }`.

### `StageStrip` (static, landing)
- **Purpose**: Read-only illustration of the 9 stages.
- **Props**: `{ stages: string[] }` (default: the 9 pipeline stages).

---

## Progress

### `ProgressTimeline`
- **Purpose**: Visualizes `completed_steps` + `current_step` as a timeline.
- **Props**: `{ currentStep: string|null, completedSteps: string[] }`.
- **Data**: progress payload.
- **State**: none (derived from props).
- **Interactions**: hover a stage → stage detail tooltip.
- **API**: fed by hook (`useResearchStream` / `useResearchJob`).

### `StageItem`
- **Purpose**: One timeline node: icon, label, state (`pending`|`active`|`done`).
- **Props**: `{ label, state, index? }`.

### `AgentActivityIndicator`
- **Purpose**: "Agent: fact_check" mono readout + subtle pulse while running.
- **Props**: `{ stage: string|null }`.

### `StepCounter`
- **Purpose**: "Step 4 / 9" style readout (display only — never a fixed max).
- **Props**: `{ completedCount, currentLabel? }`.

### `ProgressHeader`
- **Purpose**: Workspace header while running: query, status badge, elapsed time.
- **Props**: `{ query, status, jobId, startedAt? }`.

---

## Report

### `ReportViewer`
- **Purpose**: Renders the final report with meta + inline citation links.
- **Props**: `{ result: ResearchResult }`.
- **Data**: `result.report` (markdown), `result.confidence`, citations.
- **State**: reading position, expanded sections.
- **Interactions**: citation refs `[1]` scroll to citation panel.
- **API**: fed from status endpoint.

### `MarkdownRenderer`
- **Purpose**: Safe markdown → HTML (headings, lists, tables, code, links).
- **Props**: `{ markdown: string, onCitationClick?(index) }`.
- **Constraint**: sanitize HTML; do not render raw HTML from the backend.

### `ReportSection`
- **Purpose**: A titled section of the report with optional divider.
- **Props**: `{ title?, children }`.

### `ConfidenceBadge`
- **Purpose**: Confidence indicator (`high`/`medium`/`low`/unknown).
- **Props**: `{ confidence?: string }`.
- **State**: derived tone + label.

### `ReportMeta`
- **Purpose**: Meta strip: query, status, confidence, duration, source count, citation count.
- **Props**: `{ query, status, confidence?, durationMs?, counts? }`.

### `ReportActions`
- **Purpose**: Copy query, copy report, save to history, new research.
- **Props**: `{ query, report, onNewResearch }`.

---

## Evidence

### `EvidencePanel`
- **Purpose**: Container for evidence items (also used live during research).
- **Props**: `{ items: Evidence[], loading?, empty? }`.

### `EvidenceCard`
- **Purpose**: One evidence item: id (E1…), type badge, text, source link, metadata.
- **Props**: `{ item: Evidence }`.
- **Interactions**: expand/collapse long text; open source link.

### `EvidenceItemRow`
- **Purpose**: Compact evidence row for the live rail.
- **Props**: `{ id, sourceType, title?, url?, snippet? }`.

### `SourceLink`
- **Purpose**: Safe external link with domain label.
- **Props**: `{ url, title?, truncated? }`.

---

## Citations

### `CitationPanel`
- **Purpose**: Container for numbered citations.
- **Props**: `{ citations: Citation[] }`.

### `CitationCard`
- **Purpose**: One citation: `[n]`, title, URL, source type, page/chunk.
- **Props**: `{ citation: Citation, onSelect? }`.

### `CitationRef`
- **Purpose**: Inline `[1]` marker in the report linking to the citation.
- **Props**: `{ index, onClick }`.

### `SourceChip`
- **Purpose**: Small source tag (domain + type).
- **Props**: `{ url?, type? }`.

---

## Fact checks

### `FactCheckList`
- **Purpose**: Container for claim verdicts.
- **Props**: `{ checks: FactCheck[] }`.

### `FactCheckItem`
- **Purpose**: Claim + verdict badge + confidence + evidence refs.
- **Props**: `{ check: FactCheck }`.

### `VerdictBadge`
- **Purpose**: `supported` / `unsupported` / `needs more research` badge.
- **Props**: `{ verdict?: string }`.

### `ClaimRow`
- **Purpose**: Compact claim text row (used in claims list).
- **Props**: `{ claim: string, index? }`.

---

## History

### `HistoryList`
- **Purpose**: List of past research items (client-side, localStorage).
- **Props**: `{ items: HistoryItem[], onOpen, onDelete? }`.

### `HistoryItem`
- **Purpose**: One row: query, date, status, confidence, snippet.
- **Props**: `{ item: HistoryItem, onOpen, onDelete? }`.

### `HistoryEmptyState`
- **Purpose**: Empty history call-to-action.
- **Props**: `{ onCreate }`.

### `HistoryStore` (lib, not a component)
- **Purpose**: localStorage read/write for history snapshots.
- **API**: none (client-side only).

---

## Forms

### `SearchField`
- **Purpose**: Inline filter input (history).
- **Props**: `{ value, onChange, placeholder }`.

### `Label` / `FieldError`
- **Purpose**: Form label + inline validation message.
- **Props**: `Label { children, htmlFor }` · `FieldError { message? }`.

---

## Feedback

### `StatusBadge`
- **Purpose**: Job status pill (`queued`|`running`|`completed`|`failed`).
- **Props**: `{ status: JobStatus }`.

### `Toast`
- **Purpose**: Transient notifications (saved, copied, network error).
- **Props**: `{ tone: "info"|"success"|"error", message, onDismiss }`.

### `InlineError`
- **Purpose**: Contextual error block with retry.
- **Props**: `{ title, message?, onRetry? }`.

### `FullPageError`
- **Purpose**: Unrecoverable state (backend down, 404 job).
- **Props**: `{ title, message?, action?: { label, onClick } }`.

### `ErrorBoundaryState`
- **Purpose**: React error-boundary fallback.
- **Props**: `{ onReset }`.

### `EmptyState`
- **Purpose**: Generic empty state with tone + CTA.
- **Props**: `{ tone: "info"|"muted", title, body?, action? }`.

### `Skeleton`
- **Purpose**: Shimmer placeholder block.
- **Props**: `{ className?, lines? }`.

### `Spinner`
- **Purpose**: Inline loading indicator.
- **Props**: `{ size?: "sm"|"md"|"lg", label? }`.

### `CopyButton`
- **Purpose**: Copy-to-clipboard with "Copied" feedback.
- **Props**: `{ text, label? }`.

### `RetryButton`
- **Purpose**: Retry an action.
- **Props**: `{ onClick, label? }`.

---

## Responsive / mobile

### `MobileNav`
- **Purpose**: Bottom tab bar wrapper (New Research, History).
- **Props**: `{ active, onNavigate }`.

### `SlideOverPanel`
- **Purpose**: Right rail on mobile as a slide-over.
- **Props**: `{ open, onClose, children }`.

### `BottomSheet`
- **Purpose**: Detail panel from bottom on small screens.
- **Props**: `{ open, onClose, children }`.

### `MobileTabs`
- **Purpose**: Horizontally scrollable tab bar.
- **Props**: `{ tabs, active, onChange }`.

---

## Hooks (data layer glue — not components)

| Hook | Purpose | API dependency |
|---|---|---|
| `useHealth` | Backend reachability check | `GET /health` |
| `useResearchJob(jobId)` | Poll status until terminal; expose result/error | `GET /research/{job_id}` |
| `useResearchStream(jobId)` | Subscribe to SSE; reconnect; expose progress | `GET /research/{job_id}/stream` |
| `useResearchFlow` | Full submit → workspace → report state machine | `POST /research` + stream + status |

State model these hooks must expose:
`IDLE → SUBMITTING → QUEUED → RUNNING → COMPLETED | FAILED`, plus
`currentStep`, `completedSteps`, `result`, `error`.
