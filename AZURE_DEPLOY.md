# Hướng dẫn Deploy lên Azure Container Apps

## Yêu cầu

- **Azure CLI** — kiểm tra: `az --version`. Cài: https://docs.microsoft.com/cli/azure/install-azure-cli
- **Docker Desktop** — kiểm tra: `docker --version`. Cài: https://www.docker.com/products/docker-desktop/
- Python 3.11+ (để chạy local)

## Các bước thực hiện

### 1. Đăng nhập Azure

```bash
az login
```

Trình duyệt sẽ mở ra, đăng nhập tài khoản Azure của bạn.

### 2. Tạo Resource Group

```bash
az group create \
    --name ai-agent-rg \
    --location southeastasia
```

`--location southeastasia` = Singapore (gần Việt Nam, ping thấp). Có thể đổi thành `eastasia` (Hong Kong) hoặc `japaneast`.

### 3. Tạo Azure Container Registry (ACR) — nơi chứa Docker image

```bash
az acr create \
    --resource-group ai-agent-rg \
    --name aiagent24h \
    --sku Basic \
    --admin-enabled true
```

`--name` phải là **global unique** — nếu `aiagent24h` bị trùng, đặt tên khác (vd: `aiagent24h<số>`).

### 4. Build Docker image & Push lên ACR

```bash
az acr build \
    --registry aiagent24h \
    --image ai-agent:latest \
    --file Dockerfile \
    .
```

Lệnh này sẽ build image từ source code và push trực tiếp lên ACR (không cần Docker Desktop).

### 5. Tạo Azure Container Apps Environment

```bash
az containerapp env create \
    --name ai-agent-env \
    --resource-group ai-agent-rg \
    --location southeastasia
```

### 6. Tạo Storage Account + Azure Files share (cho SQLite)

Azure Files giúp file `agent.db` không bị mất khi container restart.

```bash
# Tạo storage account
az storage account create \
    --name aiagentstorage \
    --resource-group ai-agent-rg \
    --location southeastasia \
    --sku Standard_LRS

# Lấy storage key
STORAGE_KEY=$(az storage account keys list \
    --resource-group ai-agent-rg \
    --account-name aiagentstorage \
    --query "[0].value" \
    --output tsv)

# Tạo file share
az storage share create \
    --name agent-data \
    --account-name aiagentstorage \
    --account-key "$STORAGE_KEY"
```

### 7. Tạo Container App

```bash
az containerapp create \
    --name ai-agent \
    --resource-group ai-agent-rg \
    --environment ai-agent-env \
    --registry-server aiagent24h.azurecr.io \
    --image aiagent24h.azurecr.io/ai-agent:latest \
    --cpu 0.5 \
    --memory 1Gi \
    --min-replicas 0 \
    --max-replicas 1 \
    --secrets \
        telegram-token="8744574018:AAGV_ir4w3TbW5KOnrL0NDrnwBiV27nBouU" \
        llm-api-key="sk-5c71cc425d214660a426c3c073a4e204" \
    --env-vars \
        LLM_API_KEY=secretref:llm-api-key \
        LLM_BASE_URL=https://api.deepseek.com \
        LLM_MODEL=deepseek-chat \
        TELEGRAM_BOT_TOKEN=secretref:telegram-token \
        DEFAULT_TELEGRAM_CHAT_ID=1996293590 \
        DATABASE_PATH=/app/data/agent.db \
        CACHE_TTL_SECONDS=300 \
        APP_VERSION=0.1.0 \
    --target-port 80 \
    --ingress external
```

Giải thích tham số:
- `--min-replicas 0` — scale xuống 0 khi không dùng (tiết kiệm tiền)
- `--max-replicas 1` — chỉ chạy 1 instance (SQLite không support concurrent writes)
- `--secrets` — lưu mật khẩu dạng Secret (mã hoá)
- `secretref:` — tham chiếu đến secret ở trên
- `--ingress external` — cho phép truy cập từ Internet

#### 7b. Mount Azure Files vào Container App

```bash
STORAGE_KEY=$(az storage account keys list \
    --resource-group ai-agent-rg \
    --account-name aiagentstorage \
    --query "[0].value" \
    --output tsv)

# Đăng ký storage mount cho Container App environment
az containerapp env storage set \
    --name ai-agent-env \
    --resource-group ai-agent-rg \
    --storage-name agentdata \
    --azure-file-account-name aiagentstorage \
    --azure-file-account-key "$STORAGE_KEY" \
    --azure-file-share-name agent-data \
    --access-mode ReadWrite

# Gắn volume vào Container App
az containerapp update \
    --name ai-agent \
    --resource-group ai-agent-rg \
    --volume "agentdata=/app/data" \
    --secret-volume-mount "/mnt/secrets"
```

### 8. Kiểm tra

Lấy URL của app:

```bash
az containerapp show \
    --name ai-agent \
    --resource-group ai-agent-rg \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv
```

Kết quả sẽ là `ai-agent.xxx.southeastasia.azurecontainerapps.io`.

Kiểm tra health endpoint:

```bash
curl https://ai-agent.xxx.southeastasia.azurecontainerapps.io/health
```

Kết quả mong đợi: `{"status": "ok", "version": "0.1.0"}`

### 9. Xem logs

```bash
az containerapp logs show \
    --name ai-agent \
    --resource-group ai-agent-rg \
    --follow
```

### 10. Cập nhật khi có code mới

```bash
az acr build --registry aiagent24h --image ai-agent:latest .
az containerapp update --name ai-agent --resource-group ai-agent-rg --image aiagent24h.azurecr.io/ai-agent:latest
```

## Kiểm tra bot Telegram

Sau khi deploy, bot sẽ tự động:
1. Poll tin nhắn từ Telegram (long polling, không cần webhook)
2. Gửi briefing tự động vào lúc 7h, 12h, 20h hàng ngày

Gửi tin nhắn bất kỳ tới bot `@phamtnt_AI_Agent_bot` để kiểm tra.

## Xoá toàn bộ tài nguyên (khi không dùng nữa)

```bash
az group delete --name ai-agent-rg --yes --no-wait
```

Lệnh này xoá **tất cả** (Resource Group + Container App + Registry + Storage). Không mất thêm phí.

## Chi phí tham khảo

| Thành phần | Giá |
|------------|-----|
| Container Apps (0.5 CPU, 1GB, scale-to-zero) | ~$5-10/tháng |
| Container Registry (Basic) | ~$5/tháng |
| Azure Files (1GB) | ~$0.10/tháng |
| **Tổng** | **~$10-15/tháng** |

Khi không có request, Container Apps scale xuống 0 → không tốn compute, chỉ tốn storage.
