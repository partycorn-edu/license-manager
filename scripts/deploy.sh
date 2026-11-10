#!/bin/sh
# Деплой стека в Docker Swarm и проверка, что всё поднялось.
# Использование: REGISTRY=ghcr.io/user TAG=abc1234 GATEWAY_PORT=8088 ./scripts/deploy.sh
set -eu
: "${REGISTRY:?Задайте REGISTRY, например ghcr.io/user}"
: "${TAG:?Задайте TAG образов}"
GATEWAY_PORT="${GATEWAY_PORT:-8088}"
STACK=lic
TIMEOUT="${DEPLOY_TIMEOUT:-300}"

cd "$(dirname "$0")/.."

state="$(docker info --format '{{.Swarm.LocalNodeState}}')"
[ "$state" = "active" ] || { echo "ОШИБКА: Swarm не инициализирован (docker swarm init)"; exit 1; }

echo "== Память перед деплоем =="; free -m 2>/dev/null || true

sh ./scripts/create-secrets.sh

export REGISTRY TAG GATEWAY_PORT
FILES="-c swarm/stack.yml"

echo "== Деплой стека $STACK, образы $REGISTRY:*:$TAG =="
# shellcheck disable=SC2086
docker stack deploy $FILES --with-registry-auth --prune "$STACK"

echo "== Ожидание готовности (до $TIMEOUT сек) =="
elapsed=0
while :; do
  bad=0
  # строки вида "lic_api 1/1": число запущенных должно равняться нужному
  for line in $(docker stack services "$STACK" --format '{{.Name}}={{.Replicas}}' | sed 's/ (.*//'); do
    rep="${line#*=}"
    [ "${rep%/*}" = "${rep#*/}" ] || bad=1
  done
  # если Swarm сам откатил обновление, считаем деплой неудачным
  for svc in $(docker stack services "$STACK" --format '{{.Name}}'); do
    st="$(docker service inspect "$svc" --format '{{if .UpdateStatus}}{{.UpdateStatus.State}}{{end}}')"
    case "$st" in rollback_started|rollback_completed|paused)
      echo "ОШИБКА: сервис $svc в состоянии $st"; docker service ps "$svc" --no-trunc | head -8; exit 1;;
    esac
  done
  [ "$bad" = 0 ] && break
  elapsed=$((elapsed + 5))
  [ "$elapsed" -lt "$TIMEOUT" ] || { echo "ОШИБКА: сервисы не поднялись за $TIMEOUT сек"; docker stack ps "$STACK" --no-trunc | head -20; exit 1; }
  sleep 5
done

probe() { if command -v curl >/dev/null 2>&1; then curl -fsS "$1" >/dev/null; else wget -qO- "$1" >/dev/null; fi; }
echo "== Проверка через gateway на порту $GATEWAY_PORT =="
for path in /healthz /api/health /auth/health; do
  ok=0
  for _ in 1 2 3 4 5 6; do
    probe "http://127.0.0.1:$GATEWAY_PORT$path" && { ok=1; break; }
    sleep 5
  done
  [ "$ok" = 1 ] || { echo "ОШИБКА: $path не отвечает"; exit 1; }
  echo "OK $path"
done

docker stack services "$STACK"
# Запоминаем, что задеплоено, для отката
printf 'REGISTRY=%s\nGATEWAY_PORT=%s\n' "$REGISTRY" "$GATEWAY_PORT" > .deploy-env
echo "$TAG" >> .deploy-history
echo "Деплой $TAG завершён успешно"
