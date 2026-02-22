# ---------- Build stage ----------
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Runtime stage ----------
FROM python:3.11-slim

# Security: run as non-root
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app/ ./app/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
