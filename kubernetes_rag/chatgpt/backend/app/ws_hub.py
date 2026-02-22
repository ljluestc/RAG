"""WebSocket connection hub with real-time token streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

from .models import WSFrame

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}  # conversation_id -> sockets
        self._all: Set[WebSocket] = set()
        self._heartbeat_interval: float = 30.0

    async def connect(self, ws: WebSocket, conversation_id: str | None = None):
        await ws.accept()
        self._all.add(ws)
        if conversation_id:
            self._connections.setdefault(conversation_id, set()).add(ws)
        logger.info(f"WS connected (total={len(self._all)}, conv={conversation_id})")

    def disconnect(self, ws: WebSocket, conversation_id: str | None = None):
        self._all.discard(ws)
        if conversation_id and conversation_id in self._connections:
            self._connections[conversation_id].discard(ws)
            if not self._connections[conversation_id]:
                del self._connections[conversation_id]
        logger.info(f"WS disconnected (total={len(self._all)})")

    async def send_frame(self, ws: WebSocket, frame: WSFrame):
        try:
            await ws.send_text(frame.model_dump_json())
        except Exception:
            pass

    async def broadcast(self, conversation_id: str, frame: WSFrame):
        sockets = self._connections.get(conversation_id, set())
        for ws in list(sockets):
            try:
                await ws.send_text(frame.model_dump_json())
            except Exception:
                sockets.discard(ws)

    async def stream_tokens(
        self,
        ws: WebSocket,
        token_iterator,
        conversation_id: str,
    ) -> str:
        """Stream tokens from an async iterator to a WebSocket.

        Returns the full concatenated response text.
        """
        full_text = ""
        try:
            async for token in token_iterator:
                full_text += token
                frame = WSFrame(
                    event="token",
                    data={"token": token, "full_text": full_text},
                    conversation_id=conversation_id,
                )
                await ws.send_text(frame.model_dump_json())
                # tiny yield to let event loop breathe
                await asyncio.sleep(0)

            # Done frame
            done_frame = WSFrame(
                event="done",
                data={"full_text": full_text},
                conversation_id=conversation_id,
            )
            await ws.send_text(done_frame.model_dump_json())

        except WebSocketDisconnect:
            logger.info(f"Client disconnected during stream (conv={conversation_id})")
        except Exception as exc:
            logger.error(f"Stream error: {exc}")
            err_frame = WSFrame(event="error", data={"message": str(exc)})
            try:
                await ws.send_text(err_frame.model_dump_json())
            except Exception:
                pass

        return full_text

    async def heartbeat_loop(self, ws: WebSocket):
        """Send periodic pings to keep the connection alive."""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                ping = WSFrame(event="ping", data={"ts": time.time()})
                await ws.send_text(ping.model_dump_json())
        except Exception:
            pass

    @property
    def active_connections(self) -> int:
        return len(self._all)
