# InsightForge — Multi-Agent AI Research Assistant

InsightForge is an AI-powered research assistant that uses a team of specialized agents to research questions, gather web evidence, fact-check claims, and generate structured reports with citations.

Research progress is streamed live to the browser while the agents work.

## Features

* **Multi-agent research pipeline** — LangGraph coordinates 9 specialized agents:

  * Planner
  * Researcher
  * Evidence Extractor
  * Claim Extractor
  * Fact Checker
  * Citator
  * Confidence Scorer
  * Writer
  * Critic

* **AI-generated research reports** — Structured reports with citations, verified claims, and confidence scores.

* **Live research updates** — Real-time progress streaming using Server-Sent Events (SSE).

* **Web research** — Tavily provides live web search during research jobs.

* **Authentication** — JWT-based authentication with secure HTTP-only cookies.

* **Research history** — Completed research jobs are stored and can be accessed later.

* **RAG support** — Qdrant is used for vector storage and retrieval.

* **Persistent database** — PostgreSQL stores application and research data.

* **Docker deployment** — The complete application can be deployed using Docker Compose and Caddy.

## Tech Stack

| Layer            | Technology                                        |
| ---------------- | ------------------------------------------------- |
| Frontend         | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |
| Backend          | FastAPI, Python, Uvicorn                          |
| AI / Agents      | LangGraph, LangChain                              |
| LLM              | Groq — `llama-3.1-8b-instant`, OpenAI - `openai/gpt-oss-20b`                  |
| Web Search       | Tavily API                                        |
| RAG / Retrieval  | LangChain Qdrant, Qdrant vector search            |
| Embeddings       | Google Gemini — `gemini-embedding-2`              |
| Database         | PostgreSQL 16                                     |
| ORM / Migrations | SQLAlchemy, Alembic                               |
| Vector Database  | Qdrant                                            |
| Reverse Proxy    | Caddy                                             |
| Containerization | Docker, Docker Compose                            |

## Architecture

```text
User
  │
  ▼
Next.js Frontend
  │
  │ POST /research
  │ SSE /research/{id}/stream
  ▼
FastAPI Backend
  │
  ▼
LangGraph Research Pipeline
  │
  ├── Planner
  ├── Researcher ──────────► Tavily Web Search
  │       │
  │       └─────────────────► RAG Retrieval ───────► Qdrant + Gemini Embeddings
  ├── Evidence Extractor
  ├── Claim Extractor
  ├── Fact Checker
  ├── Citator
  ├── Confidence Scorer
  ├── Writer
  └── Critic
          │
          ▼
    Groq LLM
          │
          ▼
PostgreSQL + Qdrant
```

In production, Caddy acts as the reverse proxy and handles HTTPS. The frontend, backend, PostgreSQL, and Qdrant services run inside the Docker network.

## Project Structure

```text
InsightForge/
├── backend/
│   ├── app/
│   │   ├── api.py          # API endpoints and SSE streaming
│   │   ├── agents/         # AI agent implementations
│   │   ├── graph/          # LangGraph state and workflow
│   │   ├── rag/            # RAG and vector retrieval
│   │   ├── tools/          # Search and scraping tools
│   │   └── core/           # Configuration and settings
│   └── alembic/             # Database migrations
│
├── frontend/                # Next.js application
├── deploy/                  # Production deployment configuration
├── scripts/                 # Backup, restore, and health checks
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Getting Started

### Prerequisites

Install:

* Docker
* Docker Compose
* Groq API key
* Tavily API key
* Google Gemini API key

### 1. Clone the repository

```bash
git clone https://github.com/Ashwin28Toppo/InsightForge--Multi-Agent-AI-Research-Assistant.git

cd InsightForge--Multi-Agent-AI-Research-Assistant
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and add your API keys and other required configuration.

> Never commit real API keys or secrets to the repository.

### 3. Start the application

```bash
docker compose up -d --build
```

### 4. Run database migrations

```bash
docker compose exec backend sh -c "cd /app/backend && alembic upgrade head"
```

### 5. Open the application

| Service          | URL                        |
| ---------------- | -------------------------- |
| Frontend         | http://localhost:3001      |
| Backend API      | http://localhost:8000      |
| Swagger API Docs | http://localhost:8000/docs |

## Environment Variables

Copy `.env.example` to `.env` and configure the required variables.

| Variable                   | Required | Purpose             |
| -------------------------- | -------- | ------------------- |
| `GROQ_API_KEY`             | Yes      | Groq LLM access     |
| `TAVILY_API_KEY`           | Yes      | Web search          |
| `GOOGLE_API_KEY`           | Yes      | Gemini embeddings   |
| `AUTH_JWT_SECRET`          | Yes      | JWT signing secret  |
| `POSTGRES_USER`            | Compose  | PostgreSQL username |
| `POSTGRES_PASSWORD`        | Compose  | PostgreSQL password |
| `POSTGRES_DB`              | Compose  | PostgreSQL database |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | Backend API URL     |

Additional configuration options are available in `.env.example`, including model settings, CORS, TTL, and other application settings.

## Local Development

Docker is recommended for running the complete application, but the backend and frontend can also be started separately.

### Backend

```bash
.venv/Scripts/python.exe -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

If `DATABASE_URL` is not configured, the backend can run using in-memory storage for local development.

## Production Deployment

Production deployment is configured through the `deploy/` directory.

```bash
cp deploy/.env.production.example deploy/.env.production
```

Configure:

* `DOMAIN`
* `POSTGRES_PASSWORD`
* `AUTH_JWT_SECRET`
* Groq API key
* Tavily API key
* Google API key

Then start the production stack:

```bash
docker compose \
  --env-file deploy/.env.production \
  -p insightforge-prod \
  up -d --build
```

Run database migrations:

```bash
docker compose \
  -p insightforge-prod \
  exec backend sh -c "cd /app/backend && alembic upgrade head"
```

Caddy automatically manages HTTPS certificates through Let's Encrypt when the configured domain points to the server.

For detailed deployment and maintenance instructions, see [`deploy/README.md`](deploy/README.md).

## Future Improvements

* Additional LLM providers such as OpenAI and Anthropic
* User document uploads for private RAG knowledge bases
* PDF and Markdown report exports
* Multi-user workspaces
* Shared research history
* Improved research evaluation and agent performance monitoring

## License

This project is intended for educational and research purposes.
