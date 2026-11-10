# syntax=docker/dockerfile:1
# Контекст сборки: корень репозитория (нужны и frontend/, и gateway/)

# ---- этап 1: собираем Vue-приложение ----
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- этап 2: в образе только nginx и готовая статика, запуск не от root ----
FROM nginxinc/nginx-unprivileged:1.27-alpine
USER root
RUN mkdir -p /etc/nginx/extra && chown nginx:nginx /etc/nginx/extra
USER nginx
COPY gateway/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/healthz || exit 1
