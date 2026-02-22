"""Conversation manager — in-memory store (Phase 2 moves to Postgres)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .models import (
    Conversation,
    ConversationDetail,
    ConversationStatus,
    ConversationSummary,
    Message,
    PluginID,
    Role,
)

logger = logging.getLogger(__name__)


class ConversationManager:
    """In-memory conversation store.

    Replace the internal dict with the DB layer (db.py) in Phase 2.
    """

    def __init__(self):
        self._store: Dict[str, Conversation] = {}

    # -- CRUD ------------------------------------------------------------------

    def create(
        self,
        model: str = "gpt-4o-mini",
        plugins: List[PluginID] | None = None,
        system_prompt: str | None = None,
    ) -> Conversation:
        conv = Conversation(model=model, plugins=plugins or [])
        if system_prompt:
            conv.messages.append(
                Message(role=Role.system, content=system_prompt)
            )
        self._store[conv.id] = conv
        logger.info(f"Created conversation {conv.id}")
        return conv

    def get(self, conversation_id: str) -> Optional[Conversation]:
        return self._store.get(conversation_id)

    def get_or_create(self, conversation_id: str | None, **kwargs) -> Conversation:
        if conversation_id and conversation_id in self._store:
            return self._store[conversation_id]
        return self.create(**kwargs)

    def list_conversations(self, status: ConversationStatus | None = None) -> List[ConversationSummary]:
        convs = self._store.values()
        if status:
            convs = [c for c in convs if c.status == status]
        else:
            convs = [c for c in convs if c.status != ConversationStatus.deleted]

        return sorted(
            [
                ConversationSummary(
                    id=c.id,
                    title=c.title,
                    message_count=len(c.messages),
                    model=c.model,
                    status=c.status,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in convs
            ],
            key=lambda s: s.updated_at,
            reverse=True,
        )

    def detail(self, conversation_id: str) -> Optional[ConversationDetail]:
        c = self.get(conversation_id)
        if not c:
            return None
        return ConversationDetail(
            id=c.id,
            title=c.title,
            messages=c.messages,
            model=c.model,
            plugins=c.plugins,
            status=c.status,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )

    def delete(self, conversation_id: str) -> bool:
        c = self.get(conversation_id)
        if not c:
            return False
        c.status = ConversationStatus.deleted
        c.updated_at = datetime.utcnow()
        return True

    def rename(self, conversation_id: str, title: str) -> bool:
        c = self.get(conversation_id)
        if not c:
            return False
        c.title = title
        c.updated_at = datetime.utcnow()
        return True

    # -- Message helpers -------------------------------------------------------

    def add_message(self, conversation_id: str, message: Message) -> Optional[Message]:
        c = self.get(conversation_id)
        if not c:
            return None
        c.messages.append(message)
        c.updated_at = datetime.utcnow()

        # Auto-title from first user message
        if c.title == "New conversation" and message.role == Role.user:
            c.title = message.content[:60].strip() + ("…" if len(message.content) > 60 else "")

        return message

    def get_context_messages(
        self, conversation_id: str, max_turns: int = 20
    ) -> List[Dict[str, str]]:
        """Return message dicts suitable for LLM context window."""
        c = self.get(conversation_id)
        if not c:
            return []
        msgs = c.messages[-max_turns:]
        return [{"role": m.role.value, "content": m.content} for m in msgs]
