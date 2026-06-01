#!/usr/bin/env python3
"""Typer CLI for Binance Futures Testnet order placement."""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bot import config
from bot.client import BinanceAPIError, BinanceFuturesClient
from bot.logging_config import get_logger, setup_logging
from bot.orders import OrderManager, OrderResult
from bot.validators import normalize_symbol, validate_order_inputs

app = typer.Typer(
    name="trading-bot",
    help="Binance USDT-M Futures Testnet trading CLI",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()
logger = get_logger(__name__)

# Binance error hints — margin issues are the usual testnet gotcha
_ERROR_HINTS: dict[int, str] = {
    -2019: "Insufficient margin — fund your testnet wallet at https://testnet.binancefuture.com",
    -1111: "Precision error — check lot size and tick size for this symbol",
    -4164: "Order's notional below minimum — increase quantity",
    -1102: "Missing or invalid parameter — double-check symbol, side, and prices",
    -1021: "Timestamp out of sync — check your system clock",
    -2015: "Invalid API key — verify API_KEY in .env matches testnet keys",
    -4120: "Conditional orders must use the Algo Order API (this bot routes STOP_LIMIT there automatically)",
}


def _ensure_credentials() -> None:
    if not config.API_KEY or not config.API_SECRET:
        _print_validation_error(
            "credentials",
            "API_KEY and API_SECRET must be set in .env (see .env.example)",
        )
        raise typer.Exit(code=1)


def _field_from_value_error(exc: ValueError) -> tuple[str, str]:
    message = str(exc)
    field = "input"
    for name in ("symbol", "side", "order_type", "quantity", "price", "stop_price"):
        if name in message:
            field = name
            break
    return field, message


def _print_validation_error(field: str, reason: str) -> None:
    console.print(
        Panel(
            f"[bold red]Field:[/] {field}\n[bold red]Reason:[/] {reason}",
            title="Validation Error",
            border_style="red",
        )
    )


def _suggest_api_fix(err: BinanceAPIError) -> str:
    if err.error_code is not None and err.error_code in _ERROR_HINTS:
        return _ERROR_HINTS[err.error_code]
    lower = err.msg.lower()
    if "margin" in lower or "balance" in lower:
        return "Check your testnet USDT balance with: python cli.py check-balance"
    if "precision" in lower:
        return "Round quantity/price to the symbol's step size"
    return "See Binance Futures API docs for this error code"


def _print_api_error(err: BinanceAPIError) -> None:
    hint = _suggest_api_fix(err)
    console.print(
        Panel(
            f"[bold]HTTP status:[/] {err.status_code}\n"
            f"[bold]Binance code:[/] {err.error_code}\n"
            f"[bold]Message:[/] {err.msg}\n\n"
            f"[dim]Likely fix:[/] {hint}",
            title="API Error",
            border_style="red",
        )
    )


def _order_request_table(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
) -> Table:
    table = Table(title="Order Request", box=box.ROUNDED, show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Symbol", symbol)
    table.add_row("Side", side)
    table.add_row("Type", order_type)
    table.add_row("Quantity", str(quantity))
    table.add_row("Price", str(price) if price is not None else "n/a")
    table.add_row("Stop Price", str(stop_price) if stop_price is not None else "n/a")
    return table


def _order_response_table(result: OrderResult) -> Table:
    table = Table(title="Exchange Response", box=box.ROUNDED, show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    is_algo = "algoId" in result.raw_response
    table.add_row("algoId" if is_algo else "orderId", str(result.order_id))
    table.add_row("algoStatus" if is_algo else "status", result.status)
    table.add_row("executedQty", str(result.executed_qty))
    table.add_row("avgPrice", str(result.avg_price))
    return table


def _print_order_success(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
    result: OrderResult,
) -> None:
    console.print(_order_request_table(symbol, side, order_type, quantity, price, stop_price))
    console.print(_order_response_table(result))
    console.print("[bold green]Order placed successfully[/]")


def _print_dry_run(payload: dict, endpoint: str) -> None:
    lines = "\n".join(f"  {k}: {v}" for k, v in payload.items())
    console.print(
        Panel(
            f"[yellow]Dry run — no API call made[/]\n\n{lines}",
            title=f"Would send to {endpoint}",
            border_style="yellow",
        )
    )


@app.command("place-order")
def place_order(
    symbol: str = typer.Option(..., "--symbol", help="Trading pair, e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", help="MARKET, LIMIT, or STOP_LIMIT"),
    quantity: float = typer.Option(..., "--quantity", help="Order quantity"),
    price: Optional[float] = typer.Option(None, "--price", help="Limit price"),
    stop_price: Optional[float] = typer.Option(None, "--stop-price", help="Stop trigger price"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate only, do not place"),
) -> None:
    """Place a futures order on testnet."""
    setup_logging()
    try:
        validated = validate_order_inputs(symbol, side, order_type, quantity, price, stop_price)
    except ValueError as exc:
        field, reason = _field_from_value_error(exc)
        _print_validation_error(field, reason)
        raise typer.Exit(code=1) from exc

    if dry_run:
        payload = OrderManager.build_dry_run_payload(validated)
        console.print(
            _order_request_table(
                validated.symbol,
                validated.side,
                validated.order_type,
                validated.quantity,
                validated.price,
                validated.stop_price,
            )
        )
        _print_dry_run(payload, OrderManager.dry_run_endpoint(validated.order_type))
        return

    _ensure_credentials()
    try:
        with BinanceFuturesClient() as client:
            manager = OrderManager(client)
            result = manager.place_validated_order(validated)
    except BinanceAPIError as exc:
        _print_api_error(exc)
        raise typer.Exit(code=1) from exc

    _print_order_success(
        validated.symbol,
        validated.side,
        validated.order_type,
        validated.quantity,
        validated.price,
        validated.stop_price,
        result,
    )


@app.command("check-balance")
def check_balance() -> None:
    """Show USDT futures wallet balance."""
    setup_logging()
    _ensure_credentials()
    try:
        with BinanceFuturesClient() as client:
            balances = client.get_account_balance()
    except BinanceAPIError as exc:
        _print_api_error(exc)
        raise typer.Exit(code=1) from exc

    usdt = next((b for b in balances if b.get("asset") == "USDT"), None)
    table = Table(title="Futures Balance", box=box.ROUNDED)
    table.add_column("Asset", style="cyan")
    table.add_column("Wallet", justify="right")
    table.add_column("Available", justify="right")
    if usdt:
        table.add_row(
            "USDT",
            str(usdt.get("balance", "0")),
            str(usdt.get("availableBalance", "0")),
        )
    else:
        table.add_row("USDT", "0", "0")
    console.print(table)


@app.command("order-status")
def order_status(
    symbol: str = typer.Option(..., "--symbol", help="Trading pair"),
    order_id: int = typer.Option(..., "--order-id", help="Exchange order or algo ID"),
    algo: bool = typer.Option(
        False,
        "--algo",
        help="Query via Algo Order API (required for STOP_LIMIT / TP orders)",
    ),
) -> None:
    """Query an existing order by ID."""
    setup_logging()
    try:
        normalized = normalize_symbol(symbol)
    except ValueError as exc:
        field, reason = _field_from_value_error(exc)
        _print_validation_error(field, reason)
        raise typer.Exit(code=1) from exc

    _ensure_credentials()
    try:
        with BinanceFuturesClient() as client:
            if algo:
                data = client.get_algo_order(order_id)
            else:
                data = client.get_order(normalized, order_id)
    except BinanceAPIError as exc:
        _print_api_error(exc)
        raise typer.Exit(code=1) from exc

    title_id = data.get("algoId") or data.get("orderId") or order_id
    table = Table(title=f"Order {title_id}", box=box.ROUNDED)
    algo_keys = (
        "symbol", "algoId", "algoStatus", "side", "orderType", "quantity",
        "triggerPrice", "price", "actualOrderId", "actualPrice",
    )
    standard_keys = (
        "symbol", "orderId", "status", "side", "type", "origQty",
        "executedQty", "avgPrice", "price", "stopPrice",
    )
    for key in algo_keys if algo else standard_keys:
        if key in data:
            table.add_row(key, str(data[key]))
    console.print(table)


def _run_interactive() -> None:
    """Questionary-driven flow when cli.py is invoked with no args."""
    import questionary
    from questionary import Style

    setup_logging()
    style = Style([("highlighted", "bold fg:cyan")])

    console.print(Panel("Interactive order placement (testnet)", border_style="cyan"))

    symbol = questionary.text(
        "Symbol (e.g. BTCUSDT):",
        validate=lambda t: bool(t.strip()) or "Symbol required",
        style=style,
    ).ask()
    if symbol is None:
        raise typer.Exit()

    side = questionary.select("Side:", choices=["BUY", "SELL"], style=style).ask()
    if side is None:
        raise typer.Exit()

    order_type = questionary.select(
        "Order type:",
        choices=["MARKET", "LIMIT", "STOP_LIMIT"],
        style=style,
    ).ask()
    if order_type is None:
        raise typer.Exit()

    qty_str = questionary.text(
        "Quantity:",
        validate=lambda t: _interactive_positive(t, "quantity"),
        style=style,
    ).ask()
    if qty_str is None:
        raise typer.Exit()

    price_val: Optional[float] = None
    stop_val: Optional[float] = None

    if order_type in ("LIMIT", "STOP_LIMIT"):
        p = questionary.text(
            "Limit price:",
            validate=lambda t: _interactive_positive(t, "price"),
            style=style,
        ).ask()
        if p is None:
            raise typer.Exit()
        price_val = float(p)

    if order_type == "STOP_LIMIT":
        s = questionary.text(
            "Stop price:",
            validate=lambda t: _interactive_positive(t, "stop_price"),
            style=style,
        ).ask()
        if s is None:
            raise typer.Exit()
        stop_val = float(s)

    dry = questionary.confirm("Dry run only (no API call)?", default=False, style=style).ask()

    place_order(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=float(qty_str),
        price=price_val,
        stop_price=stop_val,
        dry_run=bool(dry),
    )


def _interactive_positive(value: str, field: str) -> bool | str:
    try:
        if float(value) <= 0:
            return f"{field} must be positive"
    except ValueError:
        return f"{field} must be a number"
    return True


def main() -> None:
    """Entry point — interactive mode when no subcommand is given."""
    if len(sys.argv) == 1:
        try:
            _run_interactive()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/]")
            raise typer.Exit(code=0) from None
        return
    app()


if __name__ == "__main__":
    main()
