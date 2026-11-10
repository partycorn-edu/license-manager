#!/bin/sh
# Создаёт docker secrets для стека, если их ещё нет. Уже существующие не трогает.
# Использование: ./scripts/create-secrets.sh
# Пароль admin можно задать заранее: ADMIN_PASSWORD=... ./scripts/create-secrets.sh
set -eu

# случайная строка из 32 символов
gen() { head -c 48 /dev/urandom | base64 | tr -d '/+=\n' | head -c 32; }

exists() { docker secret inspect "$1" >/dev/null 2>&1; }

make() { # имя, значение, показывать ли пароль
  if exists "$1"; then
    echo "секрет $1 уже есть, пропускаю"
  else
    printf '%s' "$2" | docker secret create "$1" - >/dev/null
    echo "создан секрет $1"
    [ "${3:-}" = "show" ] && echo "  >>> значение: $2 (запишите, повторно оно не показывается)"
  fi
  return 0
}

make lic_db_password "$(gen)"
make lic_jwt_secret "$(gen)"
make lic_admin_password "${ADMIN_PASSWORD:-$(gen)}" show
make lic_grafana_password "${GRAFANA_ADMIN_PASSWORD:-$(gen)}" show
