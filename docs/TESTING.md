# Тестирование и проверки

## Автотесты бэкенда

Что проверяется (24 теста):
- ограничение числа мест, дубли назначений, просроченная лицензия, нельзя уменьшить места ниже выданных;
- расчёт срока: бессрочная, истекающая, просроченная, граничные дни;
- дашборд: итоги по местам, списки истекающих и просроченных;
- воркер: создаёт уведомления один раз и не дублирует;
- авторизация: вход, неверный пароль, токен подписан чужим секретом, просроченный токен, роли admin и viewer, управление пользователями;
- ключ лицензии отдаётся только в маске;
- `/health` и `/metrics`.

Тесты идут на SQLite в памяти, Docker не нужен.

```powershell
cd backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements\dev.txt
pytest -q
ruff check .
```

Ожидание: `24 passed` и `All checks passed!`.
Ограничение: SQLite не проверяет блокировку строки (`FOR UPDATE`) и advisory lock. Они работают только на PostgreSQL, поэтому их проверяет только smoke-тест и ручная проверка в compose.

## Сборка фронтенда

```powershell
cd frontend
npm install
npm run build
```

Ожидание: `built in ...`, папка `dist`.

## Проверка стека целиком

```powershell
docker compose up -d --build
docker compose ps
curl.exe -s http://localhost:8080/healthz
curl.exe -s http://localhost:8080/api/health
curl.exe -s http://localhost:8080/auth/health
```

Ожидание: `ok` и два ответа `{"status":"ok",...}`. Эту же проверку делает smoke-тест в CI.

Проверка, что без токена нельзя:

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8080/api/software
```

Ожидание: `401`.

## Проверка отказоустойчивости в compose

**Падение api.**

```powershell
docker compose kill api
docker compose ps
```

Ожидание: контейнер перезапускается (`restart: unless-stopped`) и снова `healthy` через 20 секунд. Пока он лежит, gateway отвечает 502 на `/api/`.

**Падение БД.**

```powershell
docker compose stop postgres
curl.exe -s -w " %{http_code}" http://localhost:8080/api/health
docker compose start postgres
```

Ожидание: пока БД остановлена, `/api/health` отвечает 503 (а не зависает), после старта БД всё работает без перезапуска сервисов.

**Redis необязателен.**

```powershell
docker compose stop redis
```

Откройте дашборд: он продолжает работать, в логах api предупреждение «Redis недоступен». Для полностью выключенного Redis поставьте `REDIS_ENABLED=false`.

**Данные переживают перезапуск.**

```powershell
docker compose down
docker compose up -d
```

Ожидание: лицензии на месте (том `pgdata` сохранён). После `docker compose down -v` данные удаляются.

**Воркер.**

```powershell
docker compose logs -f worker
```

Ожидание: каждые `WORKER_INTERVAL_SECONDS` секунд строка «Проверка завершена, новых уведомлений: N». Остановите воркер (`docker compose stop worker`), healthcheck пометит его unhealthy, если он завис, а не остановлен.

## Нагрузочная проверка (по желанию)

```powershell
1..200 | ForEach-Object { Invoke-WebRequest http://localhost:8080/healthz -UseBasicParsing | Out-Null }
```

Затем посмотрите панель «Запросы в секунду» в Grafana.

## Проверка в кластерах

Сценарии для Swarm и Kubernetes: [SWARM.md](SWARM.md) и [K8S.md](K8S.md).

## Частые ошибки

| Симптом | Причина и решение |
|---|---|
| `ModuleNotFoundError: common` при pytest | запускайте из папки `backend` |
| `pytest` не найден | не активировано виртуальное окружение |
| `curl` в PowerShell странно ведёт себя | используйте `curl.exe`, а не `curl` (это алиас на другую команду) |
| `502 Bad Gateway` сразу после запуска | api ещё стартует, подождите несколько секунд |
