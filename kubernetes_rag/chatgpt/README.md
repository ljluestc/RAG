# ChatGPT RAG — Full-Stack Build

Complete ChatGPT-style system with multi-provider LLM routing, conversations, plugins, RAG retrieval, real-time streaming, and full Docker infrastructure.

## Quick Start

```bash
# 1. Copy your API keys
cp .env.example .env  # edit with your OPENAI_API_KEY / ANTHROPIC_API_KEY

# 2. Launch the full stack
docker compose up --build

# 3. Open the UI
open http://localhost:8000
```

## Architecture

| Component | Directory | Tech |
|-----------|-----------|------|
| Backend API | `backend/app/` | FastAPI, WebSocket, Prometheus |
| Database | `backend/app/schema.sql` | PostgreSQL 15, SQLAlchemy async |
| Frontend | `frontend/index.html` | Vanilla HTML/CSS/JS (no build step) |
| Monitoring | `monitoring/` | Prometheus + Grafana |
| C++ Scheduler | `cpp/` | C++17 thread pool + priority queue |
| Load Testing | `cpp/load_simulator.py` | asyncio + aiohttp |

## Phases

### Phase 1 — Core Backend
- **LLM Router** (`llm_router.py`): OpenAI, Anthropic, Local providers with retry + fallback chain
- **Plugin System** (`plugin_manager.py`): ABC + Web Search, Code Interpreter, RAG Lookup
- **Conversations** (`conversation_manager.py`): In-memory CRUD with auto-titling
- **Rate Limiter** (`rate_limiter.py`): Dual token-bucket (RPM + TPM per user)
- **RAG Service** (`rag_service.py`): Wraps parent project's retriever + generator
- **WebSocket Hub** (`ws_hub.py`): Connection manager with real-time token streaming

### Phase 2 — PostgreSQL
- Full SQL schema (`schema.sql`): users, conversations, messages, plugins, usage_logs
- SQLAlchemy async ORM (`db.py`) with connection pooling and CRUD helpers

### Phase 3 — Background Workers
- `workers.py`: asyncio.Queue-based embedding worker with retry, backpressure

### Phase 4 — Docker Compose Stack
- 6 services: backend, PostgreSQL, Redis, Kafka (KRaft), Prometheus, Grafana
- Grafana dashboard with request rate, latency percentiles, WebSocket connections, errors

### Phase 5 — C++ Inference Scheduler
- `inference_scheduler.cpp`: Multi-threaded priority-queue batch scheduler
- `load_simulator.py`: Async load tester measuring p50/p95/p99 latency

### Phase 6 — Frontend
- Full ChatGPT-style UI with conversation sidebar, streaming, plugins, citations, benchmark

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/models` | List available models |
| POST | `/api/chat` | Send chat message (non-streaming) |
| WS | `/ws/chat` | WebSocket streaming chat |
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations/:id` | Get conversation detail |
| DELETE | `/api/conversations/:id` | Delete conversation |
| GET | `/api/plugins` | List plugins |
| POST | `/api/benchmark` | Compare models side-by-side |

## Building the C++ Scheduler

```bash
cd cpp
mkdir build && cd build
cmake .. && make
./inference_scheduler --workers 4 --batch 8 --requests 200
```

## Load Testing

```bash
pip install aiohttp
python cpp/load_simulator.py --url http://localhost:8000 --concurrency 20 --total 200
```
