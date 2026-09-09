import base64
import datetime as dt
import hmac
import json
from hashlib import sha256

import httpx

from app.config import settings


class OKXError(Exception):
    pass


def _timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{dt.datetime.now(dt.timezone.utc).microsecond // 1000:03d}Z"


class OKXClient:
    """عميل موقّع لـ OKX v5 REST API. Spot فقط."""

    def __init__(self) -> None:
        self.base_url = settings.okx_rest_base
        self.api_key = settings.okx_api_key
        self.api_secret = settings.okx_api_secret
        self.passphrase = settings.okx_api_passphrase
        self.demo = settings.okx_demo

    def _sign(self, timestamp: str, method: str, path: str, body: str) -> str:
        prehash = f"{timestamp}{method}{path}{body}"
        mac = hmac.new(self.api_secret.encode(), prehash.encode(), sha256)
        return base64.b64encode(mac.digest()).decode()

    def _headers(self, method: str, path: str, body: str) -> dict:
        timestamp = _timestamp()
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": self._sign(timestamp, method, path, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        if self.demo:
            headers["x-simulated-trading"] = "1"
        return headers

    async def _request(self, method: str, path: str, params: dict | None = None, body: dict | None = None,
                        signed: bool = True) -> dict:
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        full_path = path + query
        body_str = json.dumps(body) if body else ""
        headers = self._headers(method, full_path, body_str) if signed else {}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10) as client:
            resp = await client.request(method, full_path, headers=headers,
                                         content=body_str if body else None)
        data = resp.json()
        if data.get("code") not in ("0", 0, None):
            raise OKXError(f"OKX API error {data.get('code')}: {data.get('msg')} ({path})")
        return data

    # ---- بيانات السوق (عامة، لا تحتاج توقيع) ----

    async def get_candles(self, inst_id: str, bar: str = "15m", limit: int = 100) -> list[list[str]]:
        data = await self._request("GET", "/api/v5/market/candles",
                                    params={"instId": inst_id, "bar": bar, "limit": limit}, signed=False)
        return data["data"]

    async def get_order_book(self, inst_id: str, depth: int = 20) -> dict:
        data = await self._request("GET", "/api/v5/market/books",
                                    params={"instId": inst_id, "sz": depth}, signed=False)
        return data["data"][0]

    async def get_ticker(self, inst_id: str) -> dict:
        data = await self._request("GET", "/api/v5/market/ticker",
                                    params={"instId": inst_id}, signed=False)
        return data["data"][0]

    async def get_instrument(self, inst_id: str) -> dict:
        data = await self._request("GET", "/api/v5/public/instruments",
                                    params={"instType": "SPOT", "instId": inst_id}, signed=False)
        return data["data"][0]

    # ---- حساب وأوامر (تحتاج توقيع) ----

    async def get_balance(self, ccy: str | None = None) -> dict:
        params = {"ccy": ccy} if ccy else None
        data = await self._request("GET", "/api/v5/account/balance", params=params)
        return data["data"][0]

    async def place_market_buy_quote(self, inst_id: str, quote_amount: str) -> dict:
        """شراء بمبلغ محدد بعملة التسعير (USDT)."""
        body = {
            "instId": inst_id,
            "tdMode": "cash",
            "side": "buy",
            "ordType": "market",
            "sz": quote_amount,
            "tgtCcy": "quote_ccy",
        }
        data = await self._request("POST", "/api/v5/trade/order", body=body)
        return data["data"][0]

    async def place_market_sell_base(self, inst_id: str, base_amount: str) -> dict:
        """بيع كمية محددة من الأصل الأساسي."""
        body = {
            "instId": inst_id,
            "tdMode": "cash",
            "side": "sell",
            "ordType": "market",
            "sz": base_amount,
            "tgtCcy": "base_ccy",
        }
        data = await self._request("POST", "/api/v5/trade/order", body=body)
        return data["data"][0]

    async def get_order(self, inst_id: str, order_id: str) -> dict:
        data = await self._request("GET", "/api/v5/trade/order",
                                    params={"instId": inst_id, "ordId": order_id})
        return data["data"][0]


okx_client = OKXClient()
