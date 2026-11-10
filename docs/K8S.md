# Kubernetes (дополнительно, локально через kind)

Kubernetes здесь показывается как второй вариант кластера. Основной кластер проекта это Docker Swarm.
Проверить манифесты на живом кластере в моей среде не удалось (нет Docker). Прошла только статическая проверка: `kustomize build` и `kubeconform` (13 объектов валидны).

kind запускает «узлы» Kubernetes как контейнеры Docker. В нашем кластере 1 control-plane и 2 worker.

## Установка инструментов (Windows, PowerShell)

```powershell
winget install Kubernetes.kind
winget install Kubernetes.kubectl
kind version
kubectl version --client
```

После установки закройте и снова откройте PowerShell.

## Шаг 1. Кластер

```powershell
kind create cluster --config k8s/kind-config.yaml
kubectl get nodes
```

Ожидание: три узла `Ready` (licenses-control-plane, licenses-worker, licenses-worker2).

## Шаг 2. Ingress-контроллер

Ingress это правила входа, а контроллер это программа, которая их исполняет. Ставим ingress-nginx (вариант для kind):

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=180s
```

Ожидание: `pod/ingress-nginx-controller-... condition met`.

## Шаг 3. Образы

Вариант 1, локальные образы. Соберите их через compose и загрузите в узлы kind:

```powershell
docker compose build
kind load docker-image local/lic-api:local local/lic-auth:local local/lic-worker:local local/lic-gateway:local --name licenses
```

Вариант 2, образы из приватного GHCR:

```powershell
kubectl create namespace licenses
kubectl create secret docker-registry ghcr-pull --namespace licenses --docker-server=ghcr.io --docker-username=ВАШ_ЛОГИН --docker-password=ТОКЕН_read:packages
kubectl patch serviceaccount default --namespace licenses -p '{\"imagePullSecrets\":[{\"name\":\"ghcr-pull\"}]}'
```

Затем в `k8s-ghcr/kustomization.yaml` замените `OWNER` и `TAG` и применяйте `k8s-ghcr` вместо `k8s` на шаге 4.

## Шаг 4. Секреты и запуск

```powershell
Copy-Item k8s/secrets.env.example k8s/secrets.env
code k8s/secrets.env
kubectl apply -k k8s/
kubectl get pods -n licenses -w
```

Ожидание: все поды `Running` и `1/1` (postgres стартует первым, api и auth могут один-два раза перезапуститься, пока БД не готова). Выход из `-w`: Ctrl+C.

Приложение: http://localhost:8081 (порт задан в `kind-config.yaml`). Вход: `admin` и `ADMIN_PASSWORD` из `k8s/secrets.env`.
Демо-данные:

```powershell
kubectl exec -n licenses deploy/api -- python -m api.seed
```

## Что в манифестах

| Файл | Что это и зачем |
|---|---|
| `kind-config.yaml` | описание кластера kind: узлы и проброс порта 8081 на Ingress |
| `kustomization.yaml` | список файлов, подстановка образов и генерация Secret из `secrets.env`. Запуск одной командой `kubectl apply -k` |
| `namespace.yaml` | Namespace `licenses`: отдельное пространство, чтобы не смешивать с другими объектами |
| `configmap.yaml` | ConfigMap: несекретные настройки (адрес БД, интервалы). Попадают в поды как переменные окружения |
| Secret (создаётся из `secrets.env`) | пароль БД, секрет JWT, пароль admin. Файла с ними в Git нет |
| `postgres.yaml` | StatefulSet для БД и headless Service. `volumeClaimTemplates` создаёт диск (PVC) 1 ГБ, данные переживают перезапуск пода |
| `api.yaml`, `auth.yaml` | Deployment с 2 репликами и Service. Есть `readinessProbe` (трафик только на готовые поды), `livenessProbe` (перезапуск зависшего), `resources`, стратегия `RollingUpdate` |
| `worker.yaml` | Deployment с одной репликой без Service, проба через `worker.healthcheck` |
| `gateway.yaml` | Deployment и Service для nginx со статикой |
| `ingress.yaml` | правила входа: `/api` на api, `/auth` на auth, всё остальное на gateway |

Как поды находят друг друга: по имени Service внутри Namespace. Например, переменная `DB_HOST=postgres` указывает на Service postgres.

## Демонстрация

**Масштабирование**

```powershell
kubectl scale deployment/api -n licenses --replicas=4
kubectl get pods -n licenses -l app=api -o wide
```

Ожидание: 4 пода api на двух worker-узлах (колонка NODE).

**Самовосстановление**

```powershell
kubectl get pods -n licenses -l app=api
kubectl delete pod -n licenses ПОД_ИЗ_СПИСКА
kubectl get pods -n licenses -l app=api
```

Ожидание: пока старый под завершается, уже появляется новый.

**Отказ узла**

```powershell
docker stop licenses-worker2
kubectl get nodes
```

Ожидание: узел станет `NotReady`. Kubernetes пересоздаёт поды не сразу (по умолчанию через 5 минут), для демо удобнее удаление подов. Вернуть: `docker start licenses-worker2`.

**Rolling update**
Окно 1, непрерывная проверка:

```powershell
while ($true) { try { (Invoke-WebRequest http://localhost:8081/api/health -UseBasicParsing).StatusCode } catch { "ошибка" }; Start-Sleep -Milliseconds 300 }
```

Окно 2, смена образа (повторно загрузите образ с новым тегом в kind):

```powershell
docker tag local/lic-api:local local/lic-api:v2
kind load docker-image local/lic-api:v2 --name licenses
kubectl set image deployment/api api=local/lic-api:v2 -n licenses
kubectl rollout status deployment/api -n licenses
```

Ожидание: поды заменяются по одному, в окне 1 только `200`.

**Откат**

```powershell
kubectl rollout history deployment/api -n licenses
kubectl rollout undo deployment/api -n licenses
```

## Команды для скриншотов отчёта

```powershell
kubectl get nodes -o wide
kubectl get all,ingress,pvc,configmap,secret -n licenses
kubectl describe deployment api -n licenses
kubectl rollout status deployment/api -n licenses
```

## Удаление

```powershell
kubectl delete -k k8s/
kind delete cluster --name licenses
```

## Частые ошибки

| Симптом | Причина и решение |
|---|---|
| `ErrImagePull` или `ImagePullBackOff` у api | образ не загружен в kind. Выполните `kind load docker-image ...` (шаг 3) |
| `secrets.env: no such file` | не создан файл. Скопируйте `secrets.env.example` |
| `CreateContainerConfigError` | не найден ключ в Secret, проверьте `secrets.env` (три ключа: DB_PASSWORD, JWT_SECRET, ADMIN_PASSWORD) |
| Ingress отвечает 404 или не открывается | ingress-nginx ещё не готов (шаг 2) или не тот порт: используйте 8081 |
| postgres `Pending` | нет StorageClass. В kind по умолчанию он есть, проверьте `kubectl get sc` |
| Поды api перезапускаются в начале | это нормально, пока БД не готова |
| Вход не работает после смены пароля в `secrets.env` | админ уже создан в БД. Удалите PVC: `kubectl delete pvc -n licenses --all` и перезапустите postgres |
