# Thông Tin Deployment

## Public URL

https://ai-agent-production-466370202292.asia-southeast1.run.app/

## Platform

Platform mục tiêu: Google Cloud Run.

Môi trường local dùng Docker Compose với:

- `agent`
- `redis`

### Health Check

```bash
curl https://ai-agent-production-466370202292.asia-southeast1.run.app/health
# Kỳ vọng: {"status":"ok"}
```

### Readiness Check

```bash
curl https://ai-agent-production-466370202292.asia-southeast1.run.app/ready
# Kỳ vọng: {"status":"ready"}
```

### Bắt Buộc Authentication

```bash
curl -X POST https://ai-agent-production-466370202292.asia-southeast1.run.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Kỳ vọng: 401
```

### Test API Có API Key

```bash
curl -X POST https://ai-agent-production-466370202292.asia-southeast1.run.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Kỳ vọng: 200
```

### Test Conversation History

```bash
curl -X POST https://ai-agent-production-466370202292.asia-southeast1.run.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"What did I just say?"}'
# Kỳ vọng: response nhắc lại câu hỏi trước đó
```

### Test Rate Limit

```bash
for i in {1..15}; do
  curl -X POST https://ai-agent-production-466370202292.asia-southeast1.run.app/ask \
    -H "X-API-Key: YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"rate-test","question":"test"}'
done
# Kỳ vọng: sau một số request sẽ trả về 429
```

## Biến Môi Trường Đã Cấu Hình

Bắt buộc:

- `PORT`
- `ENVIRONMENT`
- `REDIS_URL`
- `AGENT_API_KEY`
- `JWT_SECRET`
- `LOG_LEVEL`
- `RATE_LIMIT_PER_MINUTE`
- `MONTHLY_BUDGET_USD`
- `COST_PER_REQUEST_USD`

Tuỳ chọn:

- `OPENAI_API_KEY`
- `LLM_MODEL`
- `ALLOWED_ORIGINS`

## Ghi Chú Deploy Google Cloud Run

Cloud Run không tự đọc `.env.local`. Cần dùng `--set-env-vars` hoặc `--env-vars-file`.

Ví dụ:

```bash
gcloud run deploy ai-agent-production \
  --source 06-lab-complete \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --port 8000 \
  --env-vars-file cloudrun.env.yaml
```

Với Redis, dùng Google Memorystore hoặc một managed Redis URL khác. `redis://redis:6379/0` chỉ hoạt động trong Docker Compose local.
