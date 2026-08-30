# InsightForge â€” Multi-Agent AI Research Assistant

> Submit a research question and a team of specialized AI agents plans, searches the web, extracts evidence, fact-checks claims, and writes a structured, cited report â€” streamed live to your browser.

---

## Key Features

- **Multi-agent research pipeline** â€” LangGraph orchestrates 9 specialized agents: planner, researcher, evidence extractor, claim extractor, fact-checker, citator, confidence scorer, writer, and critic
- **AI-generated reports with citations** â€” every report includes numbered sources, verified claims, and a confidence rating
- **Live progress streaming** â€” real-time research updates delivered over Server-Sent Events (SSE)
- **Web search integration** â€” Tavily powers live web research during each job
- **User authentication** â€” JWT-based auth with secure HTTP-only cookies
- **Research history** â€” completed jobs are persisted and queryable
- **Persistent storage** â€” PostgreSQL for job data, Qdrant for vector/RAG retrieval
- **Containerized deployment** â€” full stack runs via Docker Compose behind a Caddy reverse proxy with automatic HTTPS

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS v4 |
| **Backend** | FastAPI, Python, Uvicorn |
| **AI / LLM** | LangGraph (multi-agent pipeline), Groq (`llama-3.1-8b-instant`) |
| **Web Search** | Tavily API |
| **Embeddings** | Google Gemini (`gemini-embedding-2`) |
| **Database** | PostgreSQL 16 (via SQLAlchemy + Alembic) |
| **Vector Database** | Qdrant |
| **Reverse Proxy** | Caddy (automatic HTTPS via Let's Encrypt) |
| **Containerization** | Docker, Docker Compose |

---

## Architecture

```text
User (browser)
      â†“
Next.js Frontend  (port 3000/3001)
      â†“  POST /research  |  SSE /research/{id}/stream
FastAPI Backend   (port 8000)
      â†“
LangGraph Pipeline
  plan â†’ research â†’ evidence â†’ claim_extraction
       â†’ fact_check â†’ citation â†’ confidence â†’ writer â†’ critic
      â†“                    â†“
Groq LLM             Tavily Web Search
      â†“
PostgreSQL + Qdrant
```

All services are routed through **Caddy** in production (ports 80/443 only). The backend, frontend, PostgreSQL, and Qdrant are internal to the Docker network.

---

## Project Structure

```
insightforge/
â”œâ”€â”€ backend/          # FastAPI application + LangGraph pipeline
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ api.py        # HTTP endpoints, SSE, job lifecycle
â”‚   â”‚   â”œâ”€â”€ agents/       # Individual agent implementations
â”‚   â”‚   â”œâ”€â”€ graph/        # LangGraph state, nodes, compiled graph
â”‚   â”‚   â”œâ”€â”€ rag/          # RAG ingestion, chunking, embeddings, vector store
â”‚   â”‚   â”œâ”€â”€ tools/        # Web search (Tavily) and scraping utilities
â”‚   â”‚   â””â”€â”€ core/         # Configuration (pydantic-settings)
â”‚   â””â”€â”€ alembic/      # Database migrations
â”œâ”€â”€ frontend/         # Next.js frontend (App Router)
â”œâ”€â”€ deploy/           # Production deployment config (Caddy, env templates)
â”œâ”€â”€ scripts/          # Backup, restore, and health-check scripts
â”œâ”€â”€ docker-compose.yml
â”œâ”€â”€ .env.example      # Environment variable template
â””â”€â”€ requirements.txt
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- API keys for Groq, Tavily, and Google Gemini

### 1. Clone the repository

```bash
git clone https://github.com/Ashwin28Toppo/InsightForge--Multi-Agent-AI-Research-Assistant.git
cd InsightForge--Multi-Agent-AI-Research-Assistant
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Open .env and fill in your API keys and secrets
```

### 3. Start the application

```bash
docker compose up -d --build
```

### 4. Apply database migrations

```bash
docker compose exec backend sh -c "cd /app/backend && alembic upgrade head"
```

### 5. Access the app

| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## Environment Variables

Copy `.env.example` to `.env` and configure the following. **Never commit real secrets.**

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | âœ… | LLM provider (Groq) |
| `TAVILY_API_KEY` | âœ… | Web search |
| `GOOGLE_API_KEY` | âœ… | Gemini embeddings (RAG) |
| `AUTH_JWT_SECRET` | âœ… | JWT signing secret â€” use a strong random value in production |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose | PostgreSQL credentials |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | Browser-facing backend URL (default: `http://localhost:8000`) |

See `.env.example` for all optional tuning parameters (model settings, TTL, CORS, etc.).

---

## Local Development (without Docker)

```bash
# Backend
.venv/Scripts/python.exe -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000

# Frontend (from frontend/)
npm install
npm run dev   # http://localhost:3000
```

> Without `DATABASE_URL` set, the backend runs in-memory mode (no PostgreSQL needed).

---

## Production Deployment

Full production deployment uses the `deploy/` directory with a dedicated env file:

```bash
cp deploy/.env.production.example deploy/.env.production
# Fill in DOMAIN, strong POSTGRES_PASSWORD, AUTH_JWT_SECRET, and API keys

docker compose --env-file deploy/.env.production -p insightforge-prod up -d --build
docker compose -p insightforge-prod exec backend sh -c "cd /app/backend && alembic upgrade head"
```

Caddy automatically provisions a trusted TLS certificate via Let's Encrypt when `DOMAIN` is set to a real domain with a DNS A record pointing to the server. See `deploy/README.md` for full operations documentation.

---

## Future Improvements

- Support for additional LLM providers (OpenAI, Anthropic)
- User-facing document upload for RAG (private knowledge base)
- Exportable reports (PDF, Markdown download)
- Multi-user workspaces and shared research history
