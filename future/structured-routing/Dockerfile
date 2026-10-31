FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ROUTING_CACHE_PATH=/var/cache/saaristolautat/routes.sqlite3

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts ./scripts
COPY service ./service
COPY routing-graph.json external-routing-stop-index.json ./

RUN addgroup --system router \
    && adduser --system --ingroup router router \
    && mkdir -p /var/cache/saaristolautat \
    && chown -R router:router /var/cache/saaristolautat

USER router
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]

FROM runtime AS development

USER root
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
USER router

FROM runtime AS production
