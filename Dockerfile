# ---- Phase 2F Step 11: InsightForge FastAPI backend production image ----
#
# Builds the existing FastAPI application and runs it with uvicorn. Secrets
# (API keys, DATABASE_URL, AUTH_JWT_SECRET) are NOT baked into the image —
# they are injected at runtime through Compose environment configuration.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies first (layer caching: only re-installs when
# requirements.txt changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (the package root is `/app`, so `backend.app.api` resolves).
COPY backend/ backend/

EXPOSE 8000

CMD ["uvicorn", "backend.app.api:app", "--host", "0.0.0.0", "--port", "8000"]
