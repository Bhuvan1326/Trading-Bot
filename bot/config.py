"""Central configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is one level above this package (trading_bot/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Binance Futures Testnet (USDT-M)
BASE_URL: str = os.getenv("BINANCE_FUTURES_BASE_URL", "https://testnet.binancefuture.com")
DEFAULT_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
MAX_RETRIES: int = int(os.getenv("API_MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE: float = float(os.getenv("API_RETRY_BACKOFF_BASE", "0.5"))

# Credentials — never log these
API_KEY: str = os.getenv("API_KEY", "")
API_SECRET: str = os.getenv("API_SECRET", "")

# Logging
LOG_DIR: Path = PROJECT_ROOT / "logs"
LOG_FILE: Path = LOG_DIR / "trading_bot.log"
LOG_MAX_BYTES: int = 5 * 1024 * 1024
LOG_BACKUP_COUNT: int = 3

# Sensible defaults for order placement
DEFAULT_TIME_IN_FORCE: str = "GTC"
RESPONSE_TRUNCATE_CHARS: int = 500
