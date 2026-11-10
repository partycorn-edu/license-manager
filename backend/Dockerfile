# syntax=docker/dockerfile:1
# Один Dockerfile, три образа: собирается нужная цель (--target api | auth | worker).

# ---- этап 1: ставим зависимости в отдельную папку (в итоговый образ не попадает pip и кэш) ----
FROM python:3.12-slim AS deps-base
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements/ requirements/

FROM deps-base AS deps-api
RUN pip install --prefix=/install -r requirements/api.txt

FROM deps-base AS deps-auth
RUN pip install --prefix=/install -r requirements/auth.txt

FROM deps-base AS deps-worker
RUN pip install --prefix=/install -r requirements/worker.txt

# ---- этап 2: лёгкая основа для запуска, пользователь без прав root ----
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app

# ---- итоговые образы ----
FROM runtime AS api
COPY --from=deps-api /install /usr/local
COPY common common
COPY api api
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS auth
COPY --from=deps-auth /install /usr/local
COPY common common
COPY auth auth
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "auth.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS worker
COPY --from=deps-worker /install /usr/local
COPY common common
COPY worker worker
USER 10001
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD ["python", "-m", "worker.healthcheck"]
CMD ["python", "-m", "worker.main"]
