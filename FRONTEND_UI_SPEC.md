# InsightForge — Frontend UI Specification

**For Antigravity (Phase 2E frontend agent).** This is the **most important
design document** in the handoff package. Read it fully before writing any
code. Treat the reference screenshots you are given as **visual references,
not templates** — extract patterns, don't copy branding.

---

## A. Product Identity

**InsightForge** is a **multi-agent AI research assistant**: a user types a
research question and a coordinated team of AI agents researches, verifies,
cites and writes a final report — live.

The UI is designed for:

- **Professionals and knowledge workers** (analysts, researchers, PMs,
  engineers, journalists) who need *trustworthy, cited* answers — not a chat.
- Users who want to **see the work happening**: which stage the agents are on,
  what sources were found, how claims were checked, what the confidence is.

The interface should feel like:

- a **professional research workstation**
- a **modern intelligence/research product** (think Bloomberg Terminal meets a
  premium SaaS web app, not a chatbot)
- **technical but approachable** — power-user density without intimidation
- **information-dense without being cluttered** — hierarchy does the work
- **premium SaaS quality** — polished, intentional, consistent

It must **NOT** look like:

- a ChatGPT / Claude / Perplexity clone
- a generic AI chatbot (single centered column, chat bubbles, "Ask me anything" hero)
- a generic admin dashboard (left menu of icons + table-of-tables)
- a generic SaaS landing template

---

## B. UX Philosophy

### Core principles

1. **The research is the product.** Show the process: stages, sources,
   evidence, fact checks, citations. The report is the destination; the
   journey is what builds trust.
2. **Information hierarchy over decoration.** Dense data (9 stages, many
   sources, citations) must be organized by visual weight — not by cramming
   icons and badges.
3. **Instrument-like precision.** This is a *tool*, not a toy. Numbers,
   stage names, timestamps, and statuses should read like instrumentation —
   precise, consistent, quiet. Monospace for machine-readable values is
   welcome.
4. **Calm on dark, precise accents.** The product is primarily a dark
   "research lab" canvas with a warm accent used sparingly for the active
   path (current stage, primary action, key numbers).
5. **Progressive disclosure.** Overview first; details on demand
   (expandable evidence, source panels, fact-check detail). Never dump all
   detail on the landing screen.
6. **Every state is designed.** Loading, empty, error, success, and
   transitions are first-class, not afterthoughts.

### Feel

| Feeling | How |
|---|---|
| Professional | Dense but structured, consistent spacing grid, restrained color |
| Premium | Subtle depth, crisp typography, smooth 150–250 ms transitions |
| Technical | Monospace labels, precise statuses, stage names, timestamps |
| Approachable | Generous whitespace around the primary action, plain-language microcopy |
| Trustworthy | Every claim traceable → citations, sources, evidence, fact checks |

---

## C. Visual Direction

### Layout philosophy

- **Two-region model** on the research workspace:
  - **Primary region** — the report / result (or the active progress when
    running).
  - **Secondary rail** — sources, evidence, citations, fact checks
    (right-side panel on desktop, tabs/drawer on mobile).
- **Fixed app shell** (sidebar/header) + **scrollable content**. The shell
  carries identity and navigation; the content carries the research.
- **Progressive two-column only where it helps.** Never a full-width
  single-column chat layout.
- A **sidebar** (collapsible on mobile) for: New research, History, (later)
  Knowledge base. A slim **top header** for the app identity, environment
  status (backend health), and current job status.

### Spacing

- Use a **4 px base grid**. Scale: 4, 8, 12, 16, 24, 32, 48, 64.
- **Section spacing**: 32–48 px between major regions; 16–24 px inside cards.
- **Page gutter**: 24–32 px on desktop, 16 px on mobile.
- Consistent rhythm is more important than exact values — derive the final
  scale from the reference screenshots.

### Typography hierarchy

- **Display / headings**: a distinctive, slightly condensed / high-contrast
  display face (the prototype uses **Syne**). Tight tracking
  (`-0.02em` to `-0.03em`), strong weights (700–800), used for the product
  name and page-level titles only — not for body text.
- **Body**: a clean humanist sans (**DM Sans** in the prototype; equivalent
  fine). Sizes: 14–16 px body, 12–13 px secondary, 11–12 px metadata.
- **Technical / labels**: a **monospace** face (**DM Mono** in the prototype)
  for stage names, eyebrow labels, timestamps, statuses, step counts, IDs.
  Uppercase + wide letter-spacing (0.12–0.25 em) for eyebrows.
- **Scale (approx.)**: 40–56 display · 20–24 subhead · 16–18 card title ·
  14–15 body · 12–13 secondary · 11 metadata.
- Ensure at least **4.5:1 contrast** for body text on the dark canvas.

### Cards

- Cards are for **grouped evidence**, **sources**, **history items**, and
  **report sections** — not for everything.
- Card anatomy: header (monospace eyebrow + title), body, footer (metadata,
  actions). Consistent internal padding (16–20 px).
- **Border over shadow.** Hairline borders (`1px`, low-opacity) define cards;
  shadows are minimal and used for elevation on hover/overlay only.
- **Corner radius**: 10–16 px for cards; 6–10 px for inputs/buttons; full
  (pill) only for small status badges.

### Borders, shadows, radius

- Borders: `1px` hairline, ~8–15% white on dark.
- Shadows: soft, low-opacity, only for elevated states (dropdown, dialog,
  hover). Avoid heavy drop shadows.
- Radius: consistent scale derived from the screenshots (target 8/12/16).

### Icons

- **One coherent icon set** (e.g. Lucide). Stroke-based, 1.5–2 px weight.
- Icons **support meaning**, never decorate randomly. Each icon earns its place.
- Statuses/stages may use tiny glyphs (check, loader, source, citation) but
  text labels carry the meaning.

### Navigation

- **Persistent app shell**: sidebar (desktop) / bottom tab bar or hamburger
  (mobile) for *New Research*, *History*.
- **In-page navigation**: progress → report → evidence → citations as tabs or
  anchor sections within the workspace.
- **Breadcrumb / back** from a history detail to history list.
- Keyboard: `/` focuses research input; `Esc` closes panels/dialogs; arrow
  keys navigate history list; visible focus rings.

### Responsive behavior

- **Desktop-first** (this is a workstation product), but fully usable on
  tablet and mobile:
  - ≥1024 px: sidebar + primary/right-rail layout.
  - 640–1024 px: rail becomes a slide-over panel or bottom sheet.
  - <640 px: single column, sidebar → bottom tab bar, secondary rail → tabs.
- Touch targets ≥ 40 px on mobile.

### Empty states

Every empty state must: explain **why** it's empty, offer the **next action**,
and match the visual language (no giant broken-image placeholder).

Examples:
- No history yet → "Your research history will appear here." + *Start research*.
- No job selected → prompt to enter a query or pick from history.
- No sources for a report → explain the pipeline found none (edge case).

### Loading states

- **Skeletons** (shimmer blocks matching final layout) for report/history
  loading.
- **Progress timeline** for a running job (stages + current step pulse).
- **Spinners** only for small inline actions (submit, retry).
- Disable submit while a job is in flight; show a subtle "submitting" state.

### Error states

- **Inline, contextual, recoverable.** Show the safe error message the API
  provides; never show raw stack traces.
- Distinguish: network error (backend unreachable → retry), job failed
  (show `error`, allow retry), validation (422 → inline field message), 404
  (job expired → offer new research).
- A global toast system for transient errors + a full-page error state for
  unrecoverable ones.

### Success states

- Completed: clear "Research complete" moment — confidence score, time taken,
  report ready to read.
- Subtle confirmations (toast on saved history, copied citation).

---

## D. Color System

### Approach: design tokens, derived from references

Do **not** blindly pick a palette. Derive the final tokens from the reference
screenshots while keeping accessibility + consistency. Start from the
existing prototype DNA (below) and let the screenshots refine hue/contrast.

### Existing design DNA (from the Streamlit prototype — a strong starting point)

| Token | Prototype value | Notes |
|---|---|---|
| Canvas / background | `#0a0a0f` (near-black, slight blue-warm) | Dark research-lab canvas |
| Surface (cards) | `rgba(255,255,255,0.03)` | Subtle elevated surface |
| Border | `rgba(255,140,50,0.15)` | Warm hairline |
| Primary accent | `#ff8c32` → `#ff5a1a` | Warm amber/orange — *signature* |
| Text primary | `#f0ebe0` / `#e8e4dc` | Warm off-white |
| Text secondary | `#a09890` | Muted warm gray |
| Eyebrow/label | `#ff8c32` (mono, uppercase) | Technical accent |

The existing prototype uses **radial gradient glows** (very subtle) and a
thin gradient divider. The brand is **warm (amber/orange) on dark** — this
already differentiates from generic AI purple/blue.

### Token groups to define

- `color-bg` (canvas), `color-surface`, `color-surface-raised`,
  `color-border`, `color-border-strong`
- `color-text`, `color-text-muted`, `color-text-faint`
- `color-accent` (+ hover/active/muted), `color-accent-on`
- `color-success`, `color-warning`, `color-danger`, `color-info`
  (muted variants for dark backgrounds)
- Status colors should be **muted/desaturated** on dark — not neon.

### Rules

1. Derive the final hex values from the **reference screenshots' palette**
   (hue, temperature, contrast) while preserving the warm-on-dark identity.
2. Maintain **WCAG AA** contrast for text and interactive elements.
3. Use color for **state and emphasis**, never as the only signal
   (always pair with text/icon).
4. No generic AI purple/blue gradients unless the references clearly demand it.

---

## E. Component Philosophy

Components are **reusable, typed, and isolated from the API layer**. Build
small primitives and compose them. Keep a single source of truth for design
tokens (Tailwind theme / CSS variables + shadcn/ui primitives).

### Planned component inventory (grouped — see `COMPONENT_MAP.md` for detail)

- **Layout**: AppShell, Sidebar, Header, MainContent, RightRail, BottomTabBar.
- **Navigation**: SidebarNav, HistoryNav, Breadcrumb, TabBar, BackButton.
- **Research**: ResearchInput (the hero composer), SubmitButton,
  ResearchComposer (input + options), QuerySuggestions (optional).
- **Progress**: ProgressTimeline, StageItem, AgentActivityIndicator,
  CurrentStagePulse, StepCounter, ProgressHeader.
- **Report**: ReportViewer, MarkdownRenderer, ReportSection, ConfidenceBadge,
  ReportMeta (query, time, duration, score).
- **Evidence**: EvidencePanel, EvidenceCard, EvidenceItemRow, SourceLink.
- **Citations**: CitationPanel, CitationCard, CitationRef (`[1]`, `[2]` inline),
  SourceChip.
- **Fact checks**: FactCheckItem, VerdictBadge (supported / unsupported /
  needs research), ClaimRow.
- **History**: HistoryList, HistoryItem, HistoryEmptyState,
  HistoryDetailLink.
- **Forms**: SearchField, TextArea, Label, FieldError.
- **Feedback**: Toast, InlineError, ErrorBoundaryState, EmptyState,
  Skeleton, Spinner, StatusBadge.
- **Responsive/mobile**: MobileNav, SlideOverPanel, BottomSheet,
  MobileTabs.

### Component rules

1. **Presentational components receive data via props** — they never call
   the API. All fetching lives in hooks/API layer.
2. **Typed props** (TypeScript interfaces) for every component.
3. **One component = one job.** Split, don't bloat.
4. Reuse shadcn/ui primitives where they fit; extend with the design tokens.
5. Support **loading, empty, error, disabled** variants where meaningful.
6. Keyboard-accessible + visible focus for interactive components.

---

## Anti-patterns checklist (AVOID)

- ❌ Full-width single-column chat (ChatGPT/Claude look).
- ❌ Giant centered hero with a single search bar and nothing else.
- ❌ Excessive glassmorphism / frosted panels everywhere.
- ❌ Purple/blue gradient "AI" brand.
- ❌ Excessive rounded cards ("squircle soup").
- ❌ Meaningless floating animations / confetti.
- ❌ Icon-badge clutter with no information value.
- ❌ Inconsistent spacing (each screen re-invents the grid).
- ❌ Heavy shadows / neon glows.
- ❌ Hiding everything behind tabs when a rail would show it.
