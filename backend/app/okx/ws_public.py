import asyncio
import contextlib
import json
import logging
from typing import Awaitable, Callable

import websockets

from app.config import settings

logger = logging.getLogger("okx.ws_public")

Callback = Callable[[dict], Awaitable[None]]


class _OKXWSConnection:
    """اتصال WebSocket عام قابل لإعادة الاستخدام لأي نقطة اتصال (public أو business)."""

    def __init__(self, url: str, subscribe_args: list[dict], on_message: Callback, label: str) -> None:
        self.url = url
        self.subscribe_args = subscribe_args
        self.on_message = on_message
        self.label = label
        self._stop = False
        self._task: asyncio.Task | None = None

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
                async with websockets.connect(self.url, ping_interval=None) as ws:
                    logger.info("OKX %s WS connected", self.label)
                    backoff = 2
                    await ws.send(json.dumps({"op": "subscribe", "args": self.subscribe_args}))
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
                logger.warning("OKX %s WS disconnected: %s: %s, retrying in %ss",
                                self.label, type(exc).__name__, exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _pinger(self, ws) -> None:
        while True:
            await asyncio.sleep(20)
            await ws.send("ping")


class OKXPublicWS:
    """يشترك في قنوات candle15m (عبر business)، books وtickers (عبر public) لقائمة أزواج."""

    def __init__(self, symbols: list[str], on_message: Callback) -> None:
        self.symbols = symbols
        self.on_message = on_message
        self._public = _OKXWSConnection(self._public_url(), self._public_args(), on_message, "public")
        self._business = _OKXWSConnection(self._business_url(), self._business_args(), on_message, "business")

    def _public_url(self) -> str:
        if settings.okx_demo:
            return "wss://wspap.okx.com:8443/ws/v5/public?brokerId=0"
        return settings.okx_ws_public

    def _business_url(self) -> str:
        if settings.okx_demo:
            return "wss://wspap.okx.com:8443/ws/v5/business?brokerId=0"
        return "wss://ws.okx.com:8443/ws/v5/business"

    def _public_args(self) -> list[dict]:
        args = []
        for sym in self.symbols:
            args.append({"channel": "books", "instId": sym})
            args.append({"channel": "tickers", "instId": sym})
        return args

    def _business_args(self) -> list[dict]:
        return [{"channel": "candle15m", "instId": sym} for sym in self.symbols]

    async def start(self) -> None:
        await self._public.start()
        await self._business.start()

    async def stop(self) -> None:
        await self._public.stop()
        await self._business.stop()
