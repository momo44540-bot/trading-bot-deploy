import asyncio
import json

from fastapi import WebSocket


class Broadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def publish(self, message: dict) -> None:
        payload = json.dumps(message, default=str)
        dead = []
        async with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                await client.send_text(payload)
            except Exception:
                dead.append(client)
        if dead:
            async with self._lock:
                for client in dead:
                    self._clients.discard(client)


broadcaster = Broadcaster()
