#!/bin/sh
# Проверка сетевой изоляции для docker compose (локально). Запуск из корня репозитория.
# Ожидание: api видит postgres и auth, gateway видит api и auth, но gateway НЕ видит postgres.
echo "api -> postgres (должно быть доступно)"
docker compose exec -T api python -c "import socket; socket.create_connection(('postgres',5432),3); print('  доступно: postgres:5432')" || echo "  недоступно"
echo "api -> auth (должно быть доступно)"
docker compose exec -T api python -c "import urllib.request as u; print('  ', u.urlopen('http://auth:8000/health',timeout=3).read().decode())" || echo "  недоступно"
echo "worker -> auth по имени (worker не в одной сети с monitoring, но в backend-net: доступно)"
docker compose exec -T worker python -c "import socket; socket.gethostbyname('auth'); print('  имя auth резолвится')" || echo "  недоступно"
echo "gateway -> postgres (должно быть НЕдоступно: разные сети)"
docker compose exec -T gateway sh -c "nslookup postgres 127.0.0.11 >/dev/null 2>&1 && echo '  ОШИБКА изоляции: имя postgres видно' || echo '  изоляция в порядке: имя postgres не резолвится'"
