# Поднимает кластер Swarm из 3 узлов, собирает образы и деплоит стек.
# Запуск из корня репозитория: powershell -ExecutionPolicy Bypass -File swarm-demo/demo-up.ps1
$ErrorActionPreference = "Stop"
$compose = "swarm-demo/docker-compose.yml"
$adminPass = "demo-admin-123"   # только для демонстрации

Write-Host "1/6 Запуск узлов и реестра"
docker compose -f $compose up -d

Write-Host "2/6 Ожидание Docker внутри узлов"
foreach ($n in "manager", "worker1", "worker2") {
    for ($i = 0; $i -lt 40; $i++) {
        docker exec $n docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Seconds 2
    }
    if ($LASTEXITCODE -ne 0) { throw "Узел $n не запустился. См. docs/SWARM.md, раздел частых ошибок" }
}

Write-Host "3/6 Создание кластера"
$ip = docker inspect -f '{{(index .NetworkSettings.Networks "swarmdemo_default").IPAddress}}' manager
$state = docker exec manager docker info --format '{{.Swarm.LocalNodeState}}'
if ($state -ne "active") { docker exec manager docker swarm init --advertise-addr $ip | Out-Null }
$token = docker exec manager docker swarm join-token -q worker
foreach ($n in "worker1", "worker2") {
    $st = docker exec $n docker info --format '{{.Swarm.LocalNodeState}}'
    if ($st -ne "active") { docker exec $n docker swarm join --token $token "${ip}:2377" | Out-Null }
}
docker exec manager docker node ls

Write-Host "4/6 Сборка образов и отправка в локальный реестр"
docker build --target api    -t localhost:5000/lic-api:demo    backend
docker build --target auth   -t localhost:5000/lic-auth:demo   backend
docker build --target worker -t localhost:5000/lic-worker:demo backend
docker build -f gateway/Dockerfile -t localhost:5000/lic-gateway:demo .
foreach ($s in "api", "auth", "worker", "gateway") { docker push "localhost:5000/lic-${s}:demo" }

Write-Host "5/6 Копирование файлов стека на manager"
docker exec manager rm -rf /stack
docker exec manager mkdir -p /stack
docker cp swarm manager:/stack/swarm
docker cp scripts manager:/stack/scripts
docker cp monitoring manager:/stack/monitoring
docker exec manager mkdir -p /stack/gateway
docker cp gateway/monitoring-proxy.conf manager:/stack/gateway/monitoring-proxy.conf

Write-Host "6/6 Деплой стека"
docker exec -e REGISTRY=registry:5000 -e TAG=demo -e GATEWAY_PORT=8088 `
    -e ADMIN_PASSWORD=$adminPass manager sh /stack/scripts/deploy.sh

Write-Host ""
Write-Host "Готово. Приложение: http://localhost:8088  (admin / $adminPass)"
Write-Host "Команды демонстрации: docs/SWARM.md"
