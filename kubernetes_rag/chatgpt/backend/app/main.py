"""FastAPI application — ChatGPT-style backend with streaming, plugins, and RAG."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .config import Settings, get_settings
from .conversation_manager import ConversationManager
from .llm_router import LLMRouter
from .models import (
    BenchmarkEntry,
    BenchmarkRequest,
    BenchmarkResponse,
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    Message,
    PluginID,
    Role,
    TokenUsage,
    WSFrame,
)
from .plugin_manager import PluginManager
from .rag_service import RAGService
from .rate_limiter import RateLimiter
from .ws_hub import ConnectionManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ---------------------------------------------------------------------------
# Singletons (initialized in lifespan)
# ---------------------------------------------------------------------------
settings: Settings = get_settings()
conversations = ConversationManager()
router = LLMRouter(settings)
rag = RAGService()
plugins = PluginManager(rag_service=rag)
limiter = RateLimiter(rpm=settings.rate_limit_rpm, tpm=settings.rate_limit_tpm)
ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ChatGPT backend starting up")
    yield
    logger.info("ChatGPT backend shutting down")


app = FastAPI(
    title="ChatGPT RAG Backend",
    description="Multi-provider LLM backend with conversations, plugins, RAG, and streaming",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus
Instrumentator(excluded_handlers=["/metrics", "/health"]).instrument(app).expose(app, include_in_schema=False)


# ===================================================================
# REST endpoints
# ===================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.utcnow().isoformat()}


# -- Models --

@app.get("/api/models")
async def list_models():
    models = router.available_models
    return {"models": [m.model_dump() for m in models], "default": settings.default_model}


# -- Conversations --

@app.get("/api/conversations", response_model=List[ConversationSummary])
async def list_conversations():
    return conversations.list_conversations()


@app.post("/api/conversations")
async def create_conversation(model: str = "gpt-4o-mini"):
    conv = conversations.create(model=model)
    return {"id": conv.id, "title": conv.title}


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    detail = conversations.detail(conversation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if not conversations.delete(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}


@app.patch("/api/conversations/{conversation_id}/title")
async def rename_conversation(conversation_id: str, title: str = Query(...)):
    if not conversations.rename(conversation_id, title):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "title": title}


# -- Plugins --

@app.get("/api/plugins")
async def list_plugins():
    return {"plugins": [p.model_dump() for p in plugins.list_plugins()]}


# -- Chat (non-streaming) --

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Rate limit
    if not limiter.consume("default"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    t0 = time.perf_counter()

    # Get or create conversation
    conv = conversations.get_or_create(req.conversation_id, model=req.model or settings.default_model)

    # Add user message
    user_msg = Message(role=Role.user, content=req.message)
    conversations.add_message(conv.id, user_msg)

    # Run plugins if enabled
    plugin_context = ""
    if req.plugins:
        results = await plugins.run_many(req.plugins, req.message)
        plugin_texts = [r.get("result_text", "") for r in results if r.get("result_text")]
        if plugin_texts:
            plugin_context = "\n\n[Plugin results]\n" + "\n---\n".join(plugin_texts)

    # Build LLM messages
    llm_messages = conversations.get_context_messages(conv.id)
    if plugin_context:
        llm_messages.append({"role": "system", "content": plugin_context})

    # Generate
    model = req.model or conv.model
    result = await router.generate(
        messages=llm_messages,
        model=model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )

    # Record assistant message
    assistant_msg = Message(role=Role.assistant, content=result["content"])
    conversations.add_message(conv.id, assistant_msg)

    latency = round((time.perf_counter() - t0) * 1000, 1)
    usage: TokenUsage = result.get("usage", TokenUsage())

    return ChatResponse(
        conversation_id=conv.id,
        message=assistant_msg,
        usage=usage,
        model=result.get("model", model),
        latency_ms=latency,
    )


# -- Benchmark --

@app.post("/api/benchmark", response_model=BenchmarkResponse)
async def benchmark(req: BenchmarkRequest):
    model_ids = req.models or [m.id for m in router.available_models]
    entries: List[BenchmarkEntry] = []

    messages = [{"role": "user", "content": req.query}]

    for mid in model_ids:
        try:
            t0 = time.perf_counter()
            result = await router.generate(messages=messages, model=mid, temperature=req.temperature)
            latency = round((time.perf_counter() - t0) * 1000, 1)
            entries.append(BenchmarkEntry(
                model=mid,
                answer=result["content"],
                latency_ms=latency,
                tokens=result.get("usage", TokenUsage()),
            ))
        except Exception as exc:
            entries.append(BenchmarkEntry(model=mid, error=str(exc)))

    # Summary
    valid = [e for e in entries if not e.error]
    summary = {}
    if valid:
        fastest = min(valid, key=lambda e: e.latency_ms)
        cheapest = min(valid, key=lambda e: e.tokens.total)
        summary = {
            "fastest_model": fastest.model,
            "fastest_latency_ms": fastest.latency_ms,
            "cheapest_model": cheapest.model,
            "cheapest_tokens": cheapest.tokens.total,
            "models_compared": len(valid),
        }

    return BenchmarkResponse(query=req.query, results=entries, summary=summary)


# ===================================================================
# WebSocket endpoint — streaming chat
# ===================================================================

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws_manager.connect(ws)
    heartbeat_task = asyncio.create_task(ws_manager.heartbeat_loop(ws))
    conv_id: str | None = None

    try:
        while True:
            data = await ws.receive_json()
            message_text = data.get("message", "")
            conv_id = data.get("conversation_id")
            model = data.get("model", settings.default_model)
            temperature = data.get("temperature", 0.7)
            max_tokens = data.get("max_tokens", 2048)
            plugin_ids = [PluginID(p) for p in data.get("plugins", []) if p in PluginID.__members__]

            # Rate limit
            if not limiter.consume("default"):
                await ws_manager.send_frame(ws, WSFrame(event="error", data={"message": "Rate limited"}))
                continue

            # Get or create conversation
            conv = conversations.get_or_create(conv_id, model=model)
            conv_id = conv.id

            # Add user message
            user_msg = Message(role=Role.user, content=message_text)
            conversations.add_message(conv.id, user_msg)

            # Plugins
            plugin_context = ""
            if plugin_ids:
                results = await plugins.run_many(plugin_ids, message_text)
                plugin_texts = [r.get("result_text", "") for r in results if r.get("result_text")]
                if plugin_texts:
                    plugin_context = "\n\n[Plugin results]\n" + "\n---\n".join(plugin_texts)

            # Build context
            llm_messages = conversations.get_context_messages(conv.id)
            if plugin_context:
                llm_messages.append({"role": "system", "content": plugin_context})

            # Stream tokens
            token_iter = router.stream(
                messages=llm_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            full_text = await ws_manager.stream_tokens(ws, token_iter, conv.id)

            # Save assistant message
            assistant_msg = Message(role=Role.assistant, content=full_text)
            conversations.add_message(conv.id, assistant_msg)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f"WS error: {exc}")
    finally:
        heartbeat_task.cancel()
        ws_manager.disconnect(ws, conv_id)


# ===================================================================
# Admin API — agent fleet monitoring
# ===================================================================

import platform
import socket

_start_time = time.time()


@app.get("/api/admin/status")
async def admin_status():
    """This agent's status — polled by the admin dashboard."""
    uptime_s = time.time() - _start_time
    return {
        "agent_id": f"agent-{socket.gethostname()}",
        "host": f"{socket.gethostname()}:{settings.port}",
        "status": "online",
        "model": settings.default_model,
        "uptime_s": round(uptime_s),
        "active_ws": ws_manager.active_connections,
        "conversations": len(conversations._store),
        "available_models": [m.id for m in router.available_models],
        "platform": platform.platform(),
    }


@app.get("/api/admin/metrics")
async def admin_metrics():
    """Aggregate metrics for admin dashboard."""
    total_msgs = sum(len(c.messages) for c in conversations._store.values())
    return {
        "total_conversations": len(conversations._store),
        "total_messages": total_msgs,
        "active_ws": ws_manager.active_connections,
        "rate_limiter": {
            "rpm": settings.rate_limit_rpm,
            "tpm": settings.rate_limit_tpm,
        },
    }


# -- Serve frontend --

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/")
async def serve_frontend():
    index = _FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index, media_type="text/html")
    return {"message": "ChatGPT RAG Backend — see /docs"}


@app.get("/admin")
async def serve_admin():
    admin = _FRONTEND_DIR / "admin.html"
    if admin.exists():
        return FileResponse(admin, media_type="text/html")
    return {"message": "Admin dashboard not found"}


# -- Run --

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
