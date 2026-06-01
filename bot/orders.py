"""Order placement layer on top of BinanceFuturesClient."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.client import BinanceFuturesClient
from bot.config import DEFAULT_TIME_IN_FORCE
from bot.logging_config import get_logger
from bot.validators import ValidatedOrder, validate_order_inputs

logger = get_logger(__name__)


@dataclass
class OrderResult:
    """Normalized view of a placed order response."""

    order_id: int
    symbol: str
    side: str
    type: str
    status: str
    executed_qty: float
    avg_price: float
    raw_response: Dict[str, Any]


def _parse_order_response(data: Dict[str, Any]) -> OrderResult:
    """Normalize standard and algo order responses into OrderResult."""
    order_id = data.get("orderId") or data.get("algoId") or 0
    order_type = data.get("type") or data.get("orderType") or ""
    status = data.get("status") or data.get("algoStatus") or ""
    executed = data.get("executedQty") or data.get("actualQty") or 0
    avg = data.get("avgPrice") or data.get("actualPrice") or 0
    return OrderResult(
        order_id=int(order_id),
        symbol=str(data.get("symbol", "")),
        side=str(data.get("side", "")),
        type=str(order_type),
        status=str(status),
        executed_qty=float(executed or 0),
        avg_price=float(avg or 0),
        raw_response=data,
    )


def _log_intent(label: str, **fields: object) -> None:
    parts = ", ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("Placing %s: %s", label, parts)


def _log_result(result: OrderResult) -> None:
    logger.info(
        "Order response: id=%s status=%s executed=%s avg=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )


class OrderManager:
    """High-level order API — validates, logs, and delegates to the client."""

    def __init__(self, client: BinanceFuturesClient) -> None:
        self.client = client

    def place_market_order(self, symbol: str, side: str, quantity: float) -> OrderResult:
        """Place a MARKET order."""
        validated = validate_order_inputs(symbol, side, "MARKET", quantity)
        _log_intent("MARKET", symbol=validated.symbol, side=validated.side, qty=validated.quantity)
        payload = {
            "symbol": validated.symbol,
            "side": validated.side,
            "type": "MARKET",
            "quantity": validated.quantity,
        }
        response = self.client.place_order(payload)
        result = _parse_order_response(response)
        _log_result(result)
        return result

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = DEFAULT_TIME_IN_FORCE,
    ) -> OrderResult:
        """Place a LIMIT order."""
        validated = validate_order_inputs(
            symbol, side, "LIMIT", quantity, price=price, time_in_force=time_in_force
        )
        _log_intent(
            "LIMIT",
            symbol=validated.symbol,
            side=validated.side,
            qty=validated.quantity,
            price=validated.price,
        )
        payload = {
            "symbol": validated.symbol,
            "side": validated.side,
            "type": "LIMIT",
            "quantity": validated.quantity,
            "price": validated.price,
            "timeInForce": validated.time_in_force,
        }
        response = self.client.place_order(payload)
        result = _parse_order_response(response)
        _log_result(result)
        return result

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = DEFAULT_TIME_IN_FORCE,
    ) -> OrderResult:
        """
        Place a stop-limit order via the Algo Order API.

        Since Dec 2025, conditional types (STOP, TP, etc.) must use
        POST /fapi/v1/algoOrder — the legacy /fapi/v1/order returns -4120.
        """
        validated = validate_order_inputs(
            symbol,
            side,
            "STOP_LIMIT",
            quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )
        _log_intent(
            "STOP_LIMIT (algo)",
            symbol=validated.symbol,
            side=validated.side,
            qty=validated.quantity,
            price=validated.price,
            trigger=validated.stop_price,
        )
        payload = {
            "algoType": "CONDITIONAL",
            "symbol": validated.symbol,
            "side": validated.side,
            "type": "STOP",
            "quantity": validated.quantity,
            "price": validated.price,
            "triggerPrice": validated.stop_price,
            "timeInForce": validated.time_in_force,
        }
        response = self.client.place_algo_order(payload)
        result = _parse_order_response(response)
        _log_result(result)
        return result

    def place_validated_order(self, order: ValidatedOrder) -> OrderResult:
        """Route a pre-validated order to the correct placement method."""
        if order.order_type == "MARKET":
            return self.place_market_order(order.symbol, order.side, order.quantity)
        if order.order_type == "LIMIT":
            assert order.price is not None
            return self.place_limit_order(
                order.symbol, order.side, order.quantity, order.price, order.time_in_force
            )
        assert order.stop_price is not None and order.price is not None
        return self.place_stop_limit_order(
            order.symbol,
            order.side,
            order.quantity,
            order.price,
            order.stop_price,
            order.time_in_force,
        )

    @staticmethod
    def build_dry_run_payload(order: ValidatedOrder) -> Dict[str, Any]:
        """What we would POST — useful for --dry-run output."""
        if order.order_type == "MARKET":
            return {
                "symbol": order.symbol,
                "side": order.side,
                "type": "MARKET",
                "quantity": order.quantity,
            }
        if order.order_type == "LIMIT":
            return {
                "symbol": order.symbol,
                "side": order.side,
                "type": "LIMIT",
                "quantity": order.quantity,
                "price": order.price,
                "timeInForce": order.time_in_force,
            }
        return {
            "algoType": "CONDITIONAL",
            "symbol": order.symbol,
            "side": order.side,
            "type": "STOP",
            "quantity": order.quantity,
            "price": order.price,
            "triggerPrice": order.stop_price,
            "timeInForce": order.time_in_force,
        }

    @staticmethod
    def dry_run_endpoint(order_type: str) -> str:
        """REST path shown in dry-run output."""
        if order_type == "STOP_LIMIT":
            return "POST /fapi/v1/algoOrder"
        return "POST /fapi/v1/order"
