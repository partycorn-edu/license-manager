# Локальный запуск на Windows

## Что нужно

- Docker Desktop с бэкендом WSL2 (в настройках должна стоять галочка «Use the WSL 2 based engine»).
- Git и VS Code.
- Свободный порт 8080 (или другой, его можно изменить в `.env`).

Проверка:

```powershell
docker --version
docker compose version
```

Ожидание: версии выведены без ошибок. Если пишет, что Docker не запущен, откройте Docker Desktop и подождите, пока значок станет зелёным.

## Шаг 1. Настройки

```powershell
cd путь\к\license-manager
Copy-Item .env.example .env
code .env
```

Замените все значения `change_me_...` на свои. `JWT_SECRET` должен быть длинным (от 32 символов).
Файл `.env` в Git не попадает.

## Шаг 2. Запуск

8 контейнеров:

```powershell
docker compose up -d --build
```

Первый запуск идёт несколько минут: скачиваются образы и собираются свои. Ожидание в конце: строки `Started` или `Healthy` для всех сервисов.

Проверка:

```powershell
docker compose ps
```

Ожидание: у всех сервисов статус `Up` и `(healthy)`. Grafana может стать healthy через минуту.

## Шаг 3. Демо-данные

```powershell
docker compose exec api python -m api.seed
```

Ожидание: `Демо-данные созданы`. Команду можно запускать повторно, дубликаты не создаются.

## Шаг 4. Вход

| Что | Адрес | Логин и пароль |
|---|---|---|
| Приложение | http://localhost:8080 | `admin`, пароль из `ADMIN_PASSWORD` |
| Только чтение | то же | `viewer`, пароль из `VIEWER_PASSWORD` |
| Grafana | http://localhost:8080/grafana/ | `admin`, пароль из `GRAFANA_ADMIN_PASSWORD` |
| Prometheus | http://localhost:8080/prometheus/ | без входа |

Админ создаётся при первом старте сервиса auth из `ADMIN_USERNAME` и `ADMIN_PASSWORD`.
Если вы потом поменяли пароль в `.env`, а база уже создана, пароль не изменится. Либо смените пароль через раздел «Пользователи», либо удалите данные: `docker compose down -v`.

Worker проверяет лицензии раз в `WORKER_INTERVAL_SECONDS` секунд (в `.env` по умолчанию 60). Уведомления появятся в разделе «Уведомления» через минуту после демо-данных.

## Проверка сетей

Скрипт проверки (нужен sh, например Git Bash; в PowerShell выполните команды из блока ниже вручную):

```powershell
docker network ls
docker network inspect licenses_db-net
```

Ожидание в `Containers`: только `postgres`, `api`, `auth`, `worker`.

```powershell
docker network inspect licenses_frontend-net
```

Ожидание: только `gateway`.

Запросы между контейнерами по именам сервисов:

```powershell
# api видит postgres (должно получиться)
docker compose exec api python -c "import socket; socket.create_connection(('postgres',5432),3); print('postgres доступен')"
# api видит auth (должно получиться)
docker compose exec api python -c "import urllib.request as u; print(u.urlopen('http://auth:8000/health').read())"
# gateway не видит postgres (должно не получиться)
docker compose exec gateway nslookup postgres
```

Ожидание последней команды: ошибка `can't resolve` или `NXDOMAIN`. Это и есть изоляция.

Проверка, что наружу опубликован только gateway:

```powershell
docker compose ps --format "table {{.Name}}\t{{.Ports}}"
```

Ожидание: порт вида `0.0.0.0:8080->8080/tcp` только у gateway.

## Остановка

```powershell
docker compose down        # остановить, данные сохранятся
docker compose down -v     # остановить и удалить данные
```

## Работа без Docker (для отладки)

```powershell
cd backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements\dev.txt
$env:DATABASE_URL="sqlite:///dev.db"; $env:JWT_SECRET="dev"; $env:ADMIN_PASSWORD="admin123"
uvicorn auth.main:app --port 8001      # в первом окне
uvicorn api.main:app --port 8002       # во втором окне (те же переменные)
python -m api.seed
cd ..\frontend ; npm install ; npm run dev    # http://localhost:5173
```

## Частые ошибки

| Симптом | Причина и решение |
|---|---|
| `Задайте POSTGRES_PASSWORD в файле .env` | нет файла `.env`. Выполните `Copy-Item .env.example .env` |
| `port is already allocated` или `bind: Only one usage` | порт занят. Поменяйте `GATEWAY_PORT` в `.env` |
| `docker: error during connect` | Docker Desktop не запущен |
| `api` постоянно перезапускается | смотрите `docker compose logs api`. Чаще всего БД ещё стартует, подождите минуту |
| Вход не работает после смены пароля в `.env` | админ уже создан со старым паролем, см. выше |
| Grafana показывает «No data» | подождите 1 минуту и откройте приложение, чтобы появились запросы |
| В Grafana ссылка ведёт на пустую страницу | заходите по адресу со слешем в конце: `/grafana/` |
