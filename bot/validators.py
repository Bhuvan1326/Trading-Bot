"""Order input validation before any API call."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

VALID_SIDES = frozenset({"BUY", "SELL"})
VALID_ORDER_TYPES = frozenset({"MARKET", "LIMIT", "STOP_LIMIT"})


def normalize_symbol(symbol: str) -> str:
    """Validate and uppercase a trading pair symbol."""
    if not symbol or not str(symbol).strip():
        raise ValueError("symbol must be a non-empty string")
    normalized = str(symbol).strip().upper()
    if not normalized.isalnum():
        raise ValueError(
            f"symbol must be uppercase alphanumeric (e.g. BTCUSDT), got {symbol!r}"
        )
    return normalized


@dataclass(frozen=True)
class ValidatedOrder:
    """Normalized order fields ready for OrderManager."""

    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"


def _require_positive(value: float, field_name: str) -> float:
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive number, got {value!r}")
    return value


def validate_order_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "GTC",
) -> ValidatedOrder:
    """
    Validate and normalize order parameters.

    Raises ValueError with a field-specific message on invalid input.
    """
    normalized_symbol = normalize_symbol(symbol)

    normalized_side = str(side).strip().upper()
    if normalized_side not in VALID_SIDES:
        raise ValueError(f"side must be BUY or SELL, got {side!r}")

    normalized_type = str(order_type).strip().upper()
    if normalized_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"order_type must be one of MARKET, LIMIT, STOP_LIMIT, got {order_type!r}"
        )

    qty = _require_positive(float(quantity), "quantity")

    normalized_price: Optional[float] = None
    normalized_stop: Optional[float] = None

    if normalized_type in ("LIMIT", "STOP_LIMIT"):
        if price is None:
            raise ValueError(f"price is required for {normalized_type} orders")
        normalized_price = _require_positive(float(price), "price")

    if normalized_type == "STOP_LIMIT":
        if stop_price is None:
            raise ValueError("stop_price is required for STOP_LIMIT orders")
        normalized_stop = _require_positive(float(stop_price), "stop_price")

    return ValidatedOrder(
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_type,
        quantity=qty,
        price=normalized_price,
        stop_price=normalized_stop,
        time_in_force=time_in_force,
    )
