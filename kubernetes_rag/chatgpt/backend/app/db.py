"""PostgreSQL database layer — SQLAlchemy async ORM + CRUD helpers.

Provides a drop-in replacement for the in-memory ConversationManager
when Postgres is available.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from .config import get_settings


# ---------------------------------------------------------------------------
# ORM base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class UserRow(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(128), unique=True, nullable=False)
    email = Column(String(256), unique=True, nullable=True)
    api_key = Column(String(256), nullable=True)
    rpm_limit = Column(Integer, default=60)
    tpm_limit = Column(Integer, default=100_000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversations = relationship("ConversationRow", back_populates="user", cascade="all, delete-orphan")


class ConversationRow(Base):
    __tablename__ = "conversations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(256), default="New conversation")
    model = Column(String(128), default="gpt-4o-mini")
    status = Column(String(32), default="active")
    plugins = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("UserRow", back_populates="conversations")
    messages = relationship("MessageRow", back_populates="conversation", cascade="all, delete-orphan", order_by="MessageRow.created_at")


class MessageRow(Base):
    __tablename__ = "messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"))
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    name = Column(String(128), nullable=True)
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("ConversationRow", back_populates="messages")


class PluginRow(Base):
    __tablename__ = "plugins"
    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    config = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageLogRow(Base):
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    model = Column(String(128), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, nullable=True)
    endpoint = Column(String(64), nullable=True)
    status = Column(String(16), default="ok")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Engine / session factory
# ---------------------------------------------------------------------------

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db():
    """Create all tables (dev convenience — use schema.sql for production)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

async def db_create_conversation(session: AsyncSession, model: str = "gpt-4o-mini", user_id=None) -> ConversationRow:
    row = ConversationRow(model=model, user_id=user_id)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def db_get_conversation(session: AsyncSession, conversation_id: str) -> Optional[ConversationRow]:
    result = await session.execute(select(ConversationRow).where(ConversationRow.id == conversation_id))
    return result.scalar_one_or_none()


async def db_list_conversations(session: AsyncSession, user_id=None) -> List[ConversationRow]:
    stmt = select(ConversationRow).where(ConversationRow.status != "deleted").order_by(ConversationRow.updated_at.desc())
    if user_id:
        stmt = stmt.where(ConversationRow.user_id == user_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def db_add_message(session: AsyncSession, conversation_id: str, role: str, content: str, name: str | None = None) -> MessageRow:
    row = MessageRow(conversation_id=conversation_id, role=role, content=content, name=name)
    session.add(row)
    # Touch conversation updated_at
    await session.execute(
        update(ConversationRow).where(ConversationRow.id == conversation_id).values(updated_at=func.now())
    )
    await session.commit()
    await session.refresh(row)
    return row


async def db_log_usage(session: AsyncSession, **kwargs) -> UsageLogRow:
    row = UsageLogRow(**kwargs)
    session.add(row)
    await session.commit()
    return row
