# DeepFact Validator — Cloud Run 用 Dockerfile（既存社内プロダクト 構造を流用）

FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
# Trust dictionaries (source of truth for credibility scoring / propaganda detection).
# Loaded at app start; absence falls back to hardcoded dicts inside the agents but
# defeats the GitHub Actions → Cloud Build → Cloud Run YAML pipeline, so we ship them.
COPY config/ ./config/

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8080/health'); exit(0 if r.status_code == 200 else 1)"

ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 2 --log-level info
