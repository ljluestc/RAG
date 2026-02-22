"""Pydantic schemas for the ChatGPT backend."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ConversationStatus(str, Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"


class PluginID(str, Enum):
    web_search = "web_search"
    code_interpreter = "code_interpreter"
    rag_lookup = "rag_lookup"


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class Message(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    role: Role
    content: str
    name: Optional[str] = None  # plugin / tool name
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "New conversation"
    messages: List[Message] = Field(default_factory=list)
    model: str = "gpt-4o-mini"
    plugins: List[PluginID] = Field(default_factory=list)
    status: ConversationStatus = ConversationStatus.active
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# API request / response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
    stream: bool = False
    plugins: List[PluginID] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: str
    message: Message
    usage: TokenUsage
    model: str
    latency_ms: float
    citations: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    model: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    messages: List[Message]
    model: str
    plugins: List[PluginID]
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class ModelInfo(BaseModel):
    id: str
    provider: str
    name: str
    max_tokens: int = 4096
    supports_streaming: bool = True


class PluginInfo(BaseModel):
    id: PluginID
    name: str
    description: str
    enabled: bool = True


class BenchmarkRequest(BaseModel):
    query: str
    models: Optional[List[str]] = None
    temperature: float = 0.7


class BenchmarkEntry(BaseModel):
    model: str
    answer: Optional[str] = None
    latency_ms: float = 0
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    error: Optional[str] = None


class BenchmarkResponse(BaseModel):
    query: str
    results: List[BenchmarkEntry]
    summary: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# WebSocket frames
# ---------------------------------------------------------------------------

class WSFrame(BaseModel):
    """JSON frame sent over WebSocket."""
    event: str  # token | done | error | ping | pong
    data: Any = None
    conversation_id: Optional[str] = None
