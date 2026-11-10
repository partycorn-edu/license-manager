# Мониторинг: Prometheus и Grafana

## Откуда берутся метрики

Сервисы api и auth отдают метрики на `/metrics` (библиотека prometheus-fastapi-instrumentator). Это стандартные HTTP-метрики: число запросов, задержки, статусы.
Api дополнительно отдаёт свои метрики:

| Метрика | Что означает |
|---|---|
| `lic_licenses_expiring_soon` | лицензий, которые истекают в ближайшие `EXPIRY_WARN_DAYS` дней |
| `lic_licenses_expired` | просроченных лицензий |
| `lic_licenses_overused` | лицензий с перерасходом мест |
| `lic_seats_total` | мест по действующим лицензиям |
| `lic_seats_used` | занято мест |
| `lic_seats_utilization_percent` | загрузка мест в процентах |
| `lic_notifications_unread` | непрочитанных уведомлений |

Эти метрики считаются из БД в момент запроса `/metrics`. Метрики `/metrics` не доступны через gateway, их видит только Prometheus внутри сети monitoring-net.

## Как устроено

- Prometheus (`monitoring/prometheus.yml` для compose, `prometheus.swarm.yml` для Swarm) опрашивает api и auth каждые 15 секунд. В Swarm используется адрес `tasks.api`, чтобы опрашивать все реплики.
- Grafana получает источник данных и дашборд из файлов (provisioning), вручную ничего рисовать не нужно:
  - `monitoring/grafana/provisioning/datasources/prometheus.yml`
  - `monitoring/grafana/provisioning/dashboards/dashboards.yml`
  - `monitoring/grafana/dashboards/licenses.json` (дашборд «Учёт лицензий»)

Панели дашборда: занято и всего мест, загрузка, истекающие, просроченные, непрочитанные уведомления, запросы в секунду, задержка p95, ответы 5xx, доступность целей.

## Использование локально

```powershell
docker compose up -d --build
docker compose exec api python -m api.seed
```

1. Откройте http://localhost:8080/grafana/ и войдите: `admin` и пароль из `GRAFANA_ADMIN_PASSWORD`.
2. Меню Dashboards, папка Licenses, дашборд «Учёт лицензий».
3. Нажмите на сайте несколько страниц, чтобы появились запросы, и подождите минуту.

Prometheus: http://localhost:8080/prometheus/, раздел Status, Targets. Ожидание: цели `api` и `auth` в состоянии UP.

Полезные запросы в Prometheus:

```
up
max(lic_seats_utilization_percent)
sum by (job) (rate(http_requests_total[1m]))
```

Проверить метрики напрямую:

```powershell
docker compose exec api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/metrics').read().decode()[:600])"
```

## Метрики в Swarm на сервере

Prometheus внутри Swarm наружу не опубликован, поэтому метрики на сервере проще посмотреть командой:

```bash
docker exec $(docker ps -q -f name=lic_api | head -n 1) python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/metrics').read().decode()[:800])"
```

## Проверка, что метрики живые (по желанию)

Сделайте лицензию с датой окончания через 5 дней, и через минуту панель «Скоро истекают» покажет изменение.

## Частые ошибки

| Симптом | Причина и решение |
|---|---|
| Цель `api` в состоянии DOWN | сервис не готов или Prometheus не в одной сети с api. Проверьте `docker compose ps` |
| Grafana: «No data» | нет запросов к сервисам или прошло меньше минуты |
| Grafana не открывается по `/grafana` | нужен слеш в конце адреса |
| Панели статистики пустые | `lic_*` метрики появляются только если api подключился к БД, смотрите `docker compose logs api` |
| Дашборд не появился | проверьте `docker compose logs grafana` на ошибки provisioning и что файл дашборда смонтирован |
| В Swarm Prometheus не видит реплики | должен быть конфиг `prometheus.swarm.yml`, а не `prometheus.yml` |
