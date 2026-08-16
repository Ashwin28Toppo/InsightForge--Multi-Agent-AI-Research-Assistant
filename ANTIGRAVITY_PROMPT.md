# ANTIGRAVITY — Final Copy-Paste Prompt

Copy everything below into Antigravity. It is self-contained.

---

```
You are responsible ONLY for building the frontend UI for "InsightForge — a
multi-agent AI research assistant". The backend is COMPLETE (Phase 2D done),
frontend-integration ready, and must be treated as a fixed external API.

================================================================
YOUR MANDATE
================================================================

Build a polished, production-quality, NON-generic frontend. This product
must NOT look like a ChatGPT/Claude/Perplexity clone, a generic AI chatbot,
or a generic admin dashboard. It is a professional research workstation.

================================================================
STEP 0 — DO NOT START BY CODING
================================================================

Before writing any code, in order:

1. Inspect the repository at "d:/Multi Agent System" (structure, key files).
2. Read ALL of these UI handoff documents:
   - README.md
   - FRONTEND_UI_SPEC.md
   - UI_PAGES.md
   - API_FOR_FRONTEND.md
   - FOLDER_GUIDE.md
   - COMPONENT_MAP.md
3. Inspect the reference screenshots/images the user provides. Treat them as
   VISUAL REFERENCES, NOT TEMPLATES. Extract: composition, spacing,
   hierarchy, typography, interaction patterns, navigation patterns, content
   density, card structures, animations. Do NOT copy branding or assets.
4. Identify common visual patterns across the references.
5. Write a short UI implementation plan (layout model, token system, page
   inventory, component inventory).
6. Identify reusable components and page-level layouts.
7. THEN implement.

Do not immediately generate a generic dashboard. The research process and
its progress are the centerpiece of the product.

================================================================
MANDATORY READING (in this order)
================================================================

1. README.md            — architecture, flows, job lifecycle, rules.
2. FRONTEND_UI_SPEC.md  — the visual/UX specification (MOST IMPORTANT).
3. UI_PAGES.md          — every page, route, layout, states, data.
4. API_FOR_FRONTEND.md  — the exact API + SSE contract (read before ANY
                          fetch/SSE code).
5. FOLDER_GUIDE.md      — what to touch, what to NEVER touch.
6. COMPONENT_MAP.md     — the reusable component inventory.

================================================================
TECHNICAL REQUIREMENTS
================================================================

1. Use the project's selected frontend stack: Next.js (App Router) +
   TypeScript + Tailwind CSS + shadcn/ui.
2. Create the frontend under "frontend/" — do not modify the backend.
3. Build a CLEAN, ISOLATED API layer:
   - frontend/lib/api/client.ts        (fetch wrapper: base URL, JSON, errors)
   - frontend/lib/api/research.ts      (submitResearch, getJobStatus, getJobProgress)
   - frontend/lib/api/health.ts        (getHealth)
   - frontend/lib/sse/research-stream.ts (isolated SSE client)
   - frontend/lib/types/api.ts         (all API + SSE types)
   Do NOT scatter fetch() calls throughout components.
4. Base URL via NEXT_PUBLIC_API_BASE_URL (default http://127.0.0.1:8000).
5. Implement the full state model:
   IDLE → SUBMITTING → QUEUED → RUNNING → COMPLETED | FAILED
   plus current_step and completed_steps. NEVER assume a fixed number of
   steps.
6. Implement the exact frontend research workflow:
   user enters query → POST /research → receive job_id → show research
   workspace → connect SSE → receive queued/progress events → update progress
   UI → receive completed/failed → if completed: GET /research/{job_id} →
   display report + citations + evidence; if failed: show meaningful error
   state and allow retry.
7. Implement SSE correctly:
   - events: queued | progress | completed | failed (terminal).
   - completed/failed are terminal — the stream closes after.
   - SSE does NOT contain the final report — after completed, call
     GET /research/{job_id} for the result.
   - On reconnect the current state is REPLAYED (first event may be progress
     or completed). Reconnect safely with backoff; NEVER POST a new research
     job on reconnection.
   - While SSE is reconnecting you may poll GET /research/{job_id}/progress.
8. Implement report viewing (markdown renderer + sanitization).
9. Implement citations/evidence presentation (numbered citations, source
   cards, evidence items, fact-check verdicts).
10. Implement research history (CLIENT-SIDE only — localStorage. The backend
    has no history endpoint).
11. Implement loading (skeletons), error (inline + full-page), empty, and
    success states everywhere.
12. Make the UI responsive (desktop-first workstation; fully usable on
    tablet/mobile).
13. Reuse components from the COMPONENT_MAP and shadcn/ui primitives.
14. Do not introduce unnecessary dependencies.

================================================================
PRESERVATION RULES (ABSOLUTE)
================================================================

- Do NOT modify backend logic, LangGraph, agents, prompts, RAG, database/
  vector logic, API behavior, or response formats.
- Do NOT modify backend/app/api.py, backend/app/main.py, backend/app/graph/,
  backend/app/agents/, backend/app/rag/, backend/app/tools/,
  backend/app/core/, backend/tests/, or app.py (Streamlit prototype).
- Do NOT modify .env / .env.example / requirements.txt / conftest.py.
- Do NOT add authentication or PostgreSQL (out of scope).
- Preserve every API response body and SSE event format.
- Keep all backend tests green (run "cd d:/Multi Agent System &&
  .venv/Scripts/python.exe -m pytest -q" if you ever touch backend — you
  should not need to).
- Do NOT run real research requests just to test the UI (external quota).
  Use a mocked/offline pipeline, fixture data, or the documented API contract.

================================================================
DESIGN REQUIREMENTS
================================================================

- Strong visual hierarchy; consistent spacing grid; polished typography.
- Honor the existing design DNA (from the Streamlit prototype and
  FRONTEND_UI_SPEC.md): dark research-lab canvas (#0a0a0f), warm amber
  accent (#ff8c32 → #ff5a1a), Syne / DM Sans / DM Mono typography,
  instrument-like precision — unless the reference screenshots clearly
  demand a different direction.
- Derive the final palette from the reference screenshots as design tokens
  while preserving accessibility (WCAG AA) and consistency. Do not blindly
  pick colors.
- Subtle animations (150–250 ms), meaningful loading states, skeleton
  loaders, smooth transitions.
- Accessible, keyboard-friendly (visible focus, Esc/arrow handling), mobile
  support, desktop optimization.
- AVOID: excessive gradients, excessive glassmorphism, excessive rounded
  cards, giant hero sections everywhere, chatbot-style single-column chat,
  meaningless animations, excessive badges, random icons, inconsistent
  spacing, excessive shadows, generic AI purple/blue gradients.

================================================================
DELIVERABLES
================================================================

When done, report:
1. What you built (pages, layout model, component inventory).
2. How the API layer is structured.
3. How SSE + reconnection is implemented.
4. How the state machine works.
5. How history is persisted.
6. How you handled loading/error/empty/success states.
7. Responsive strategy.
8. How the reference screenshots influenced the design (patterns extracted).
9. Anything you did NOT implement and why.
```

---

## After copying the prompt

Antigravity should start at **STEP 0 — DO NOT START BY CODING**, then read the
six documents, study your reference screenshots, write a plan, and only then
build the frontend under `frontend/` while leaving the backend untouched.
