import asyncio
import contextlib
import json
import logging
from typing import Awaitable, Callable

import websockets

from app.config import settings

logger = logging.getLogger("okx.ws_public")

Callback = Callable[[dict], Awaitable[None]]


class OKXPublicWS:
    """يشترك في قنوات candle15m, books, tickers لقائمة أزواج ويعيد الاتصال تلقائيًا."""

    def __init__(self, symbols: list[str], on_message: Callback) -> None:
        self.symbols = symbols
        self.on_message = on_message
        self._stop = False
        self._task: asyncio.Task | None = None

    def _url(self) -> str:
        if settings.okx_demo:
            return "wss://wspap.okx.com:8443/ws/v5/public?brokerId=0"
        return settings.okx_ws_public

    def _subscribe_args(self) -> list[dict]:
        args = []
        for sym in self.symbols:
            args.append({"channel": "candle15m", "instId": sym})
            args.append({"channel": "books", "instId": sym})
            args.append({"channel": "tickers", "instId": sym})
        return args

    async def start(self) -> None:
        self._stop = False
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        backoff = 2
        while not self._stop:
            try:
                async with websockets.connect(self._url(), ping_interval=None) as ws:
                    logger.info("OKX public WS connected")
                    backoff = 2
                    await ws.send(json.dumps({"op": "subscribe", "args": self._subscribe_args()}))
                    ping_task = asyncio.create_task(self._pinger(ws))
                    try:
                        async for raw in ws:
                            if raw == "pong":
                                continue
                            msg = json.loads(raw)
                            if "data" in msg:
                                await self.on_message(msg)
                    finally:
                        ping_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await ping_task
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("OKX public WS disconnected: %s: %s, retrying in %ss",
                                type(exc).__name__, exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _pinger(self, ws) -> None:
        while True:
            await asyncio.sleep(20)
            await ws.send("ping")
