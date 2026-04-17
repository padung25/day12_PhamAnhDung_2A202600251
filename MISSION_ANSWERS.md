# Day 12 Lab - Câu Trả Lời Mission

## Part 1: Localhost vs Production

### Exercise 1.1: Các anti-pattern đã tìm thấy

1. Hardcoded secrets: `OPENAI_API_KEY` và `DATABASE_URL` được lưu trực tiếp trong source code.
2. Config bị hardcode: `DEBUG`, `MAX_TOKENS`, host và port không đọc từ biến môi trường.
3. Dùng `print()` để log thay vì structured logging.
4. App log cả API key, làm lộ secret trong log.
5. Không có endpoint `/health`, nên platform không biết container đã lỗi để restart.
6. App bind vào `localhost`, không phù hợp khi chạy trong container.
7. Bật `reload=True`, đây là hành vi chỉ nên dùng trong development.
8. Chưa có graceful shutdown để xử lý SIGTERM và request đang chạy.

### Exercise 1.3: Bảng so sánh

| Tính năng | Develop | Production | Vì sao quan trọng? |
|---|---|---|---|
| Config | Hardcode | Biến môi trường | Cùng một code/image có thể chạy ở dev, staging, production |
| Secrets | Nằm trong source code | Đọc từ env/secrets | Tránh lộ secret trên GitHub, Docker image hoặc log |
| Host | `localhost` | `0.0.0.0` | Container cần nhận traffic từ bên ngoài process |
| Port | Cố định `8000` | `$PORT` / settings | Cloud platform thường inject port động |
| Health check | Không có | `/health` và `/ready` | Giúp platform restart và route traffic đúng lúc |
| Logging | `print()` | JSON structured logs | Dễ search, parse và giám sát trong production |
| Shutdown | Tắt đột ngột | SIGTERM/lifespan cleanup | Cho phép request đang chạy và connection kết thúc sạch |
| Debug mode | Luôn bật | Điều khiển bằng env | Tránh reload/debug behavior trong production |

## Part 2: Docker

### Exercise 2.1: Câu hỏi về Dockerfile

1. Base image: `python:3.11`.
2. Working directory: `/app`.
3. `COPY requirements.txt` trước source code để Docker cache layer cài dependencies. Nếu chỉ sửa code mà không đổi dependencies thì build nhanh hơn.
4. `CMD` là command mặc định khi container start và dễ override. `ENTRYPOINT` định nghĩa executable chính của container và thường dùng khi muốn container luôn chạy một command cố định.

### Exercise 2.3: Multi-stage build

- Stage 1: builder cài dependencies và các build tools cần thiết.
- Stage 2: runtime chỉ copy packages đã cài và application source.
- Image production nhỏ hơn vì không giữ compiler, package manager cache và file chỉ cần lúc build.
- Runtime dùng non-root user để an toàn hơn.

So sánh image size:

- Develop: chạy `docker images my-agent:develop` để ghi kích thước chính xác.
- Production: chạy `docker images my-agent:advanced` để ghi kích thước chính xác.
- Kết quả kỳ vọng: production image nhỏ hơn single-stage development image.

### Exercise 2.4: Kiến trúc Docker Compose

Services:

- `agent`: ứng dụng FastAPI.
- `redis`: lưu shared state, rate limit và budget.
- `nginx`: reverse proxy/load balancer khi stack có bật Nginx.
- Stack advanced có thể có thêm `qdrant` để lưu vector cho RAG.

Luồng request:

```text
Client -> Nginx -> Agent -> Redis
```

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy Railway

- Screenshot service running: [screenshots/running.png](screenshots/running_03.png)

Cấu hình Railway dùng start command dạng:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Ghi chú: final project hiện được deploy lên Google Cloud Run. Railway/Render config vẫn được giữ trong repo để đối chiếu deployment config theo yêu cầu lab.

### Exercise 3.2: So sánh Render và Railway

| Chủ đề | Railway | Render |
|---|---|---|
| File cấu hình | `railway.toml` | `render.yaml` |
| Build | Nixpacks hoặc Dockerfile | Python runtime hoặc Docker runtime |
| Env vars | CLI/dashboard | Blueprint và dashboard |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Extra services | Thường cấu hình trong dashboard | Có thể khai báo Redis trong blueprint |

### Exercise 3.3: GCP Cloud Run

Deploy lên Cloud Run cần:

- Docker image build từ app.
- Environment variables cho config.
- Redis managed, ví dụ Google Memorystore, hoặc một Redis URL bên ngoài để lưu shared state.
- Endpoint `/health` và `/ready` để platform kiểm tra service.

## Part 4: API Security

### Exercise 4.1: API key authentication

API key authentication được triển khai bằng header `X-API-Key`. Nếu thiếu hoặc sai key, app trả về `401 Unauthorized`.

Test:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'
# Kỳ vọng: 401

curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Kỳ vọng: 200
```

### Exercise 4.2: JWT authentication

Luồng JWT:

1. User đăng nhập bằng username/password.
2. Server ký token có các claim như `sub`, `role`, `iat`, `exp`.
3. Client gửi `Authorization: Bearer <token>`.
4. Server verify signature và expiry của token.

JWT là stateless vì server có thể xác thực claim từ token đã ký mà không cần đọc session trong memory.

### Exercise 4.3: Rate limiting

Final app dùng Redis-backed rate limiting. Mỗi user có một Redis key cho từng phút hiện tại. Mỗi request tăng counter và Redis tự expire key.

Limit: `RATE_LIMIT_PER_MINUTE`, mặc định `10` requests/phút.

Kết quả test kỳ vọng:

```bash
for i in {1..15}; do
  curl -X POST http://localhost:8000/ask \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test","question":"test"}'
done
# Kỳ vọng: sau một số request sẽ trả về 429
```

### Exercise 4.4: Cost guard implementation

Cost guard dùng Redis key theo tháng:

```text
budget:{user_id}:{YYYY-MM}
```

Mỗi request:

1. Đọc chi phí hiện tại của user trong tháng.
2. Cộng estimated request cost.
3. Từ chối với `402` nếu vượt `MONTHLY_BUDGET_USD`.
4. Lưu tổng mới và set expiry 32 ngày.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health và readiness

- `/health` trả về `{"status":"ok"}` khi process còn sống.
- `/ready` kiểm tra Redis và trả 503 khi Redis unavailable hoặc service đang shutdown.

### Exercise 5.2: Graceful shutdown

App xử lý `SIGTERM`:

1. Dừng nhận request mới.
2. Chờ active requests hoàn thành trong giới hạn timeout.
3. Đóng Redis connection.
4. Exit sạch.

### Exercise 5.3: Stateless design

Conversation history được lưu trong Redis:

```text
history:{user_id}
```

Nhờ vậy bất kỳ instance nào khi scale cũng có thể tiếp tục cùng một conversation.

### Exercise 5.4: Load balancing

Với Docker Compose, agent có thể scale:

```bash
docker compose up --build --scale agent=3
```

Nginx có thể route traffic qua nhiều agent instances khi được cấu hình làm reverse proxy.

### Exercise 5.5: Stateless test

Test kỳ vọng:

1. Gửi `{"user_id":"test","question":"Hello"}`.
2. Gửi `{"user_id":"test","question":"What did I just say?"}`.
3. Response thứ hai nên nhắc lại câu hỏi trước đó từ Redis history.

## Part 6: Final Project

Final implementation nằm trong `06-lab-complete/`.

Đã triển khai:

- REST API với `POST /ask`.
- Conversation history trong Redis.
- Multi-stage Dockerfile.
- Config qua environment variables.
- API key authentication.
- Redis-backed rate limiting.
- Redis-backed monthly cost guard.
- `/health` và `/ready`.
- Graceful shutdown.
- JSON structured logging.
- Không commit `.env.local` chứa secret.

Minh chứng triển khai:

- Deployment dashboard: [screenshots/dashboard.png](screenshots/dashboard.png)
- Screenshot service running: [screenshots/running.png](screenshots/running.png)
- Test results: [screenshots/test.png](screenshots/test.png)
