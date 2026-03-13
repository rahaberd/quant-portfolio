import asyncio
import json
from collections.abc import Iterable

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast_json(self, payload: dict) -> None:
        message = json.dumps(payload, default=str)
        await self._broadcast(message)

    async def broadcast_many_json(self, payloads: Iterable[dict]) -> None:
        for payload in payloads:
            await self.broadcast_json(payload)

    async def _broadcast(self, message: str) -> None:
        async with self._lock:
            peers = list(self._connections)

        stale_connections: list[WebSocket] = []
        for peer in peers:
            try:
                await peer.send_text(message)
            except Exception:
                stale_connections.append(peer)

        if stale_connections:
            async with self._lock:
                for peer in stale_connections:
                    self._connections.discard(peer)
