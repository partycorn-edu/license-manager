# Docker Swarm

Swarm встроен в Docker. Он запускает сервисы по описанию в stack-файле, держит нужное число реплик, перезапускает упавшие и обновляет их по очереди.

Основные понятия:
- **node**: машина в кластере (manager управляет, worker выполняет).
- **service**: описание «запусти N копий этого образа».
- **task**: одна запущенная копия (контейнер).
- **stack**: набор сервисов, которые разворачиваются вместе.
- **overlay-сеть**: сеть, которая объединяет контейнеры на разных узлах.
- **secret** и **config**: безопасное хранение паролей и файлов настроек.

## Файлы

| Файл | Для чего |
|---|---|
| `swarm/stack.yml` | 8 сервисов, реплики 2/2/2/1, secrets, configs, Prometheus и Grafana |
| `swarm-demo/` | кластер из 3 узлов на docker:dind и скрипты |
| `scripts/deploy.sh`, `rollback.sh`, `create-secrets.sh` | деплой, откат, секреты |

Отличия stack-файла от `docker-compose.yml`:
- нет `build`, только `image` (образы берутся из реестра);
- настройки запуска лежат в блоке `deploy` (реплики, обновление, лимиты, `restart_policy`);
- нет `depends_on`: сервисы сами ждут БД (см. `init_db`) и перезапускаются, пока всё не поднимется;
- пароли только через secrets (`*_FILE`), не через `environment`;
- сети типа `overlay`.

Что в стеке есть:
- **Overlay-сети**: frontend, backend, db, monitoring (последние три internal).
- **Secrets**: `lic_db_password`, `lic_jwt_secret`, `lic_admin_password`, `lic_grafana_password`.
- **Configs**: конфиг Prometheus, конфиг проксирования Grafana для gateway, provisioning Grafana.
- **Healthcheck**: берутся из Dockerfile (api, auth, worker, gateway) и заданы в stack-файле (postgres, redis).
- **Rolling update**: `update_config` с `parallelism: 1`, `failure_action: rollback`, `monitor: 20s`.
- **restart_policy**, **resources.limits**.

## Вариант A. Кластер из 3 узлов на вашем компьютере

Узлы это контейнеры docker:dind. Это имитация настоящего кластера, но принципы те же.
Важно: этот вариант проверить в моей среде не удалось (там нет Docker). Он может потребовать правок на вашем Docker Desktop, см. «Частые ошибки».

```powershell
powershell -ExecutionPolicy Bypass -File swarm-demo/demo-up.ps1
```

Скрипт делает по шагам: запускает manager, worker1, worker2 и локальный реестр; создаёт кластер; собирает образы и отправляет в реестр; копирует stack-файлы; выполняет деплой стека.
Ожидание в конце: таблица `docker node ls` с тремя узлами и строка «Деплой demo завершён успешно». Приложение: http://localhost:8088 (admin, пароль `demo-admin-123`).

Для удобства задайте алиас для команд на manager:

```powershell
function sw { docker exec manager docker @args }
```

### Демонстрация для защиты

**1. Кластер и распределение.**

```powershell
sw node ls
sw stack services lic
sw stack ps lic
```

Ожидание: три узла Ready, сервисы с репликами, в колонке NODE видно разные узлы.

**2. Масштабирование.**

```powershell
sw service scale lic_api=4 lic_gateway=3
sw service ps lic_api
```

Ожидание: 4 задачи api на разных узлах, все Running. Вернуть: `sw service scale lic_api=1 lic_gateway=1`.

**3. Самовосстановление (убиваем контейнер).**
Узнайте узел одной из реплик api (`sw service ps lic_api`) и остановите на нём контейнер:

```powershell
docker exec worker1 docker ps --filter name=lic_api -q
docker exec worker1 sh -c 'docker rm -f $(docker ps --filter name=lic_api -q | head -n 1)'
sw service ps lic_api
```

Ожидание: старая задача `Failed` или `Shutdown`, рядом новая `Running`. Приложение продолжает отвечать.

**4. Выход узла из строя.**

```powershell
docker stop worker2
sw node ls
sw service ps lic_api
```

Ожидание: worker2 получает статус Down, его задачи через несколько секунд пересоздаются на живых узлах. Вернуть: `docker start worker2`.

**5. Плановое обслуживание узла.**

```powershell
sw node update --availability drain worker1
sw service ps lic_api
sw node update --availability active worker1
```

Ожидание: задачи уходят с worker1 на другие узлы.

**6. Обновление без простоя (rolling update).**
Откройте второе окно и запустите непрерывную проверку:

```powershell
while ($true) { try { (Invoke-WebRequest http://localhost:8088/api/health -UseBasicParsing).StatusCode } catch { "ошибка" }; Start-Sleep -Milliseconds 300 }
```

В первом окне соберите «новую версию» и обновите сервис:

```powershell
docker tag localhost:5000/lic-api:demo localhost:5000/lic-api:v2
docker push localhost:5000/lic-api:v2
sw service update --image registry:5000/lic-api:v2 lic_api
sw service ps lic_api
```

Ожидание: задачи заменяются по одной, во втором окне только `200` без `ошибка` (при 2 и более репликах api и `start-first`).

**7. Откат.**

```powershell
sw service rollback lic_api
```

Ожидание: сервис возвращается к предыдущему образу.

**8. Проверка сетей и секретов.**

```powershell
sw network ls
sw secret ls
sw config ls
sw service inspect lic_api --pretty
```

Остановить демо и удалить всё: `powershell -File swarm-demo/demo-down.ps1`.

## Вариант B. Один узел на Docker Desktop

Если dind не заработал, покажите то же самое на одном узле: реплики, масштабирование, самовосстановление и обновление работают (кроме пунктов про разные узлы).

```powershell
docker swarm init
docker compose build
$env:REGISTRY="local"; $env:TAG="local"; $env:GATEWAY_PORT="8088"
```

В stack-файле образы берутся из `REGISTRY/lic-*:TAG`, а локально собранные образы называются `local/lic-api:local`, поэтому отдельный реестр не нужен. Секреты создайте так:

```powershell
"mypassdb12345" | docker secret create lic_db_password -
"myjwtsecret_myjwtsecret_12345678" | docker secret create lic_jwt_secret -
"adminpass123" | docker secret create lic_admin_password -
"grafanapass123" | docker secret create lic_grafana_password -
docker stack deploy -c swarm/stack.yml lic
docker service ls
```

Ожидание: все сервисы `1/1`. Остановить: `docker stack rm lic`, затем `docker swarm leave --force`.

## Вариант C. Настоящий Swarm на VPS

См. [VPS.md](VPS.md). Там один узел, масштабирование ограничено памятью. Для защиты лучше показывать вариант A или B.

## Команды для скриншотов отчёта

```powershell
sw node ls
sw stack services lic
sw service ps lic_api
sw service scale lic_api=4
sw service inspect lic_api --pretty
sw network ls
sw secret ls
```

## Частые ошибки

| Симптом | Причина и решение |
|---|---|
| Узел `manager` не запускается, в логах про overlayfs или cgroup | dind не подошёл вашему Docker Desktop. Используйте вариант B |
| `x509` или `http: server gave HTTP response to HTTPS client` | узел не знает про insecure-реестр. Проверьте, что в `swarm-demo/docker-compose.yml` есть `--insecure-registry=registry:5000` и узлы пересозданы (`demo-down.ps1`, затем `demo-up.ps1`) |
| `No such image` при деплое в демо | образы не отправлены в реестр. Выполните шаг сборки из `demo-up.ps1` вручную |
| сервис `0/N` | `sw service ps lic_api --no-trunc` покажет причину |
| `secret not found` | не созданы секреты. Запустите `scripts/create-secrets.sh` |
| `network ... not found` или конфликт сетей | остались сети от прошлого деплоя. `docker stack rm lic`, подождите 20 секунд, повторите |
| Не работает вход после смены секретов | пароль БД в томе остался старым. Удалите том `lic_pgdata` вместе с секретами |
