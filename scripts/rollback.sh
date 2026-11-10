#!/bin/sh
# Откат на предыдущий (или указанный) тег образов.
# ./scripts/rollback.sh            откат на предыдущий тег из истории
# ./scripts/rollback.sh abc1234    откат на конкретный тег
set -eu
cd "$(dirname "$0")/.."
[ -f .deploy-env ] || { echo "Нет файла .deploy-env: деплой ещё не выполнялся"; exit 1; }
# shellcheck disable=SC1091
. ./.deploy-env
if [ -n "${1:-}" ]; then
  TAG="$1"
else
  TAG="$(tail -n 2 .deploy-history | head -n 1)"
  [ "$(wc -l < .deploy-history)" -ge 2 ] || { echo "В истории нет предыдущего тега"; exit 1; }
fi
echo "Откат на тег $TAG"
export REGISTRY GATEWAY_PORT TAG
exec sh ./scripts/deploy.sh
