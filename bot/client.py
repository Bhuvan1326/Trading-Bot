"""HTTP client for Binance USDT-M Futures with HMAC signing."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

from bot import config
from bot.logging_config import get_logger

logger = get_logger(__name__)

SENSITIVE_KEYS = frozenset({"signature", "apiKey"})


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response."""

    def __init__(
        self,
        status_code: int,
        error_code: Optional[int],
        msg: str,
        raw_body: Optional[dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.msg = msg
        self.raw_body = raw_body or {}
        super().__init__(f"[{error_code}] {msg}" if error_code is not None else msg)


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Strip secrets before logging."""
    return {k: v for k, v in params.items() if k not in SENSITIVE_KEYS}


def _truncate(text: str, limit: int = config.RESPONSE_TRUNCATE_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


class BinanceFuturesClient:
    """Signed REST client for Binance Futures Testnet."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or config.API_KEY
        self.api_secret = api_secret or config.API_SECRET
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else config.DEFAULT_TIMEOUT
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"X-MBX-APIKEY": self.api_key},
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "BinanceFuturesClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _sign(self, params: Dict[str, Any]) -> str:
        """HMAC-SHA256 signature over the query string."""
        query = urlencode(params, doseq=True)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _prepare_signed_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        signed = dict(params or {})
        signed["timestamp"] = int(time.time() * 1000)
        signed["signature"] = self._sign(signed)
        return signed

    def _parse_error(self, response: httpx.Response) -> BinanceAPIError:
        try:
            body = response.json()
        except ValueError:
            body = {}
        code = body.get("code")
        msg = body.get("msg", response.text or "Unknown error")
        return BinanceAPIError(
            status_code=response.status_code,
            error_code=int(code) if code is not None else None,
            msg=str(msg),
            raw_body=body if isinstance(body, dict) else {},
        )

    def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """Execute HTTP request with exponential backoff on network failures."""
        base_params = params or {}
        last_exc: Optional[Exception] = None

        for attempt in range(config.MAX_RETRIES):
            request_params = (
                self._prepare_signed_params(base_params) if signed else dict(base_params)
            )
            try:
                return self._do_request(method, endpoint, request_params)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt == config.MAX_RETRIES - 1:
                    logger.exception(
                        "Network failure after %d attempts: %s %s",
                        config.MAX_RETRIES,
                        method,
                        endpoint,
                    )
                    raise
                wait = config.RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Network error on %s %s (attempt %d/%d), retrying in %.1fs: %s",
                    method,
                    endpoint,
                    attempt + 1,
                    config.MAX_RETRIES,
                    wait,
                    exc,
                )
                time.sleep(wait)

        raise last_exc  # pragma: no cover

    def _do_request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        safe = _sanitize_params(params)
        logger.debug("→ %s %s params=%s", method, url, safe)

        try:
            response = self._client.request(method, url, params=params)
        except httpx.HTTPError:
            logger.exception("HTTP exception for %s %s", method, url)
            raise

        body_text = response.text
        logger.debug(
            "← %s %s status=%d body=%s",
            method,
            url,
            response.status_code,
            _truncate(body_text),
        )

        if not response.is_success:
            err = self._parse_error(response)
            logger.error(
                "Binance API error: status=%d code=%s msg=%s",
                err.status_code,
                err.error_code,
                err.msg,
            )
            raise err

        return response.json()

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """GET request."""
        return self._request_with_retry("GET", endpoint, params=params, signed=signed)

    def post(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """POST request (signed by default for trading endpoints)."""
        return self._request_with_retry("POST", endpoint, params=params, signed=signed)

    def get_account_balance(self) -> Dict[str, Any]:
        """Fetch futures account balance (v2)."""
        return self.get("/fapi/v2/balance", signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query a single order by ID."""
        return self.get(
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order via POST /fapi/v1/order (MARKET, LIMIT only)."""
        return self.post("/fapi/v1/order", params=params, signed=True)

    def place_algo_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Place a conditional order via POST /fapi/v1/algoOrder (STOP, TP, etc.)."""
        return self.post("/fapi/v1/algoOrder", params=params, signed=True)

    def get_algo_order(self, algo_id: int) -> Dict[str, Any]:
        """Query a single algo order by algoId."""
        return self.get(
            "/fapi/v1/algoOrder",
            params={"algoId": algo_id},
            signed=True,
        )
