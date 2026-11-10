# Развёртывание на VPS

Сервер: Linux с публичным IP. Приложение работает как Docker Swarm на одном узле. Образы берутся из приватного GHCR, их собирает CI (на самом сервере ничего не собирается).

Команды ниже выполняются на сервере по SSH. Замените `ВАШ_IP` и `deploy` на свои значения.

## 1. Проверка сервера

```bash
free -m
```

Ожидание: в строке `Mem` колонка `available` показывает свободную память. Для стека из `swarm/stack.yml` нужно около 1,4 ГБ по лимитам, для сокращённого варианта из раздела 5.1 около 600 МБ.
Если своп не настроен, создайте его (нужен root):

```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Какие порты уже заняты:

```bash
sudo ss -tlnp
```

Ожидание: список занятых портов. Выберите свободный порт для приложения, например 8088, и убедитесь, что его нет в списке.

## 2. Установка Docker

Официальный способ для Ubuntu и Debian:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
docker --version
```

Ожидание: версия Docker 27 или новее.

Пользователь для деплоя (отдельный, не root):

```bash
sudo adduser deploy
sudo usermod -aG docker deploy
```

Важно: доступ к docker почти равен root-доступу. Поэтому SSH-ключ этого пользователя нужно беречь (см. [CICD.md](CICD.md)).

## 3. Firewall

Приложение публикуется на выбранном порту, и этот порт должен быть открыт. Остальное закрыто.

```bash
sudo ufw status
sudo ufw allow 22/tcp      # SSH, обязательно до включения firewall
sudo ufw allow 8088/tcp    # порт приложения
sudo ufw enable
```

Важное предупреждение: порты, которые публикует Docker, обходят правила ufw. Это особенность Docker. Для нас это нормально, потому что наружу публикуется только gateway.
Postgres и остальные сервисы не публикуются и снаружи недоступны. Проверить: `sudo ss -tlnp` не должен показывать 5432.

Если вы не уверены, что ufw безопасно включать на сервере (можно отрезать себе SSH), лучше не включайте его, а ограничьте порты в панели хостинга.

## 4. Swarm на одном узле

```bash
docker swarm init --advertise-addr 127.0.0.1 --listen-addr 127.0.0.1:2377
```

Ожидание: `Swarm initialized: current node ... is now a manager`.
Адрес 127.0.0.1 нужен, чтобы управляющий порт 2377 не был доступен из интернета. Кластер из одного узла так и должен работать. Если позже захотите добавить узлы, потребуется внешний адрес.

## 5. Порт и память

- Приложение занимает только один порт (`GATEWAY_PORT`, по умолчанию 8088).
- Память: лимиты контейнеров в `swarm/stack.yml` в сумме около 1,4 ГБ. Это пределы, а не измеренное потребление. Если на сервере меньше памяти, уберите необязательные сервисы (раздел 5.1).
- Если памяти станет не хватать, остановите приложение (раздел 8).

### 5.1. Если памяти не хватает

Redis, Prometheus и Grafana не обязательны: приложению нужны gateway, api, auth, worker и postgres. Перед первым деплоем отредактируйте `swarm/stack.yml`:
1. Удалите сервисы `redis`, `prometheus`, `grafana`.
2. Удалите из корня файла тома `prometheus-data`, `grafana-data`, секрет `grafana_password` и configs `prometheus_yml`, `grafana_datasource`, `grafana_providers`, `grafana_dashboard`.
3. У сервиса `gateway` удалите блок `configs` с `monitoring_proxy` и сам конфиг `monitoring_proxy` внизу.
4. В `api` поставьте `REDIS_ENABLED: "false"` и удалите `REDIS_URL`.
5. Из `scripts/create-secrets.sh` удалите последнюю строку с `lic_grafana_password`.
6. Для экономии памяти уменьшите реплики api, auth и gateway до 1.

Команда `docker stack config -c swarm/stack.yml` покажет, что файл остался корректным.
После такой правки лимиты в сумме составят около 600 МБ (при одной реплике каждого сервиса). Это расчёт по лимитам, а не замер, проверьте `docker stats` (раздел 7).

## 6. Первый деплой вручную

Нужно, чтобы CI уже собрал образы (хотя бы один push в main), и чтобы был создан токен на чтение пакетов (см. [CICD.md](CICD.md)).

Вход в реестр (токен вводится в ответ на запрос пароля):

```bash
echo ВАШ_ТОКЕН | docker login ghcr.io -u ВАШ_GITHUB_ЛОГИН --password-stdin
```

Ожидание: `Login Succeeded`.

Файлы стека. На своём компьютере (PowerShell, из корня репозитория):

```powershell
tar czf deploy.tgz swarm scripts monitoring gateway/monitoring-proxy.conf
scp deploy.tgz deploy@ВАШ_IP:~/
```

На сервере:

```bash
mkdir -p ~/licenses && tar xzf ~/deploy.tgz -C ~/licenses && cd ~/licenses
REGISTRY=ghcr.io/ваш_логин_строчными TAG=abc1234 GATEWAY_PORT=8088 sh ./scripts/deploy.sh
```

`TAG` это первые 7 символов sha коммита, который собрал CI (виден в GitHub в разделе Packages и в Actions).

Что делает скрипт: создаёт секреты Swarm (если их нет), выполняет `docker stack deploy`, ждёт, пока все сервисы станут готовы, и проверяет `/healthz`, `/api/health`, `/auth/health` через порт gateway.
В конце скрипт выведет пароль admin один раз. Запишите его. Если нужен свой пароль, задайте заранее: `ADMIN_PASSWORD=мойпароль sh ./scripts/deploy.sh`.

Ожидание в конце: `Деплой abc1234 завершён успешно` и таблица сервисов, где у каждого число запущенных реплик равно нужному.

Демо-данные (по желанию):

```bash
docker exec $(docker ps -q -f name=lic_api | head -n 1) python -m api.seed
```

Откройте http://ВАШ_IP:8088.
Без https пароли идут открытым текстом. Для реального использования настройте сертификат.

## 7. Проверка потребления памяти

```bash
docker stats --no-stream
free -m
```

Ожидание: суммарное потребление контейнеров заметно ниже суммы лимитов, у `lic_postgres` обычно самый большой расход. Если `available` в `free -m` падает ниже 50 МБ, уменьшите нагрузку или остановите стек.

## 8. Как всё откатить и удалить

Остановить приложение (данные сохраняются):

```bash
docker stack rm lic
```

Удалить данные и секреты:

```bash
docker volume rm lic_pgdata
docker secret rm lic_db_password lic_jwt_secret lic_admin_password lic_grafana_password
```

Если секреты удалены, а том с БД остался, при новом деплое пароль БД не совпадёт. Удаляйте том и секреты вместе.

Выйти из Swarm и убрать Docker (по желанию):

```bash
docker swarm leave --force
sudo apt-get purge -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo rm -rf /var/lib/docker
```

Убрать правило firewall: `sudo ufw delete allow 8088/tcp`.

Откат на предыдущую версию приложения: [CICD.md](CICD.md), раздел «Откат».

## Частые ошибки

| Симптом | Причина и решение |
|---|---|
| `Cannot connect to the Docker daemon` | пользователь не в группе docker. Выполните `sudo usermod -aG docker deploy` и перезайдите по SSH |
| `unauthorized` при pull образа | токен не тот или без права `read:packages`, либо `docker login` не выполнен |
| `manifest unknown` | такого тега нет в GHCR. Проверьте sha и что CI закончился |
| `port is already allocated` | порт занят. Выберите другой `GATEWAY_PORT` |
| сервис висит `0/1` | `docker service ps lic_api --no-trunc` покажет причину. Часто не хватает памяти (`free -m`) |
| `this node is not a swarm manager` | не выполнен `docker swarm init` |
| сервер «подвис» при деплое | не хватило памяти. Включите своп и повторите, см. [CICD.md](CICD.md), раздел про нагрузку |