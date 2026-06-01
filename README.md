# Binance Futures Testnet Trading Bot

A Python CLI application for placing USDT-M Futures orders on Binance Futures Testnet. The project demonstrates API integration, request signing, input validation, structured logging, error handling, and clean software architecture.

## Repository

GitHub: https://github.com/Bhuvan1326/Trading-Bot

---

## Assignment Summary

This project was developed as part of a Python Developer technical assessment.

### Core Requirements Implemented

* MARKET Orders
* LIMIT Orders
* BUY / SELL Support
* CLI Interface
* Input Validation
* Structured Logging
* Error Handling
* Binance Futures Testnet Integration

### Additional Enhancements

* STOP_LIMIT Orders (Bonus Feature)
* Dry-Run Mode
* Interactive CLI Mode
* Retry Logic with Exponential Backoff
* Centralized Configuration Management
* Rotating Log Files

---

## Overview

This bot focuses on three key areas:

1. Securely signing and sending authenticated requests to Binance Futures Testnet.
2. Validating user inputs before API requests are made.
3. Providing a clean CLI experience with readable output and useful error messages.

The project is structured so that the Binance client, order management logic, validation layer, and CLI interface remain independent and reusable.

---

## Screenshots

<img width="1920" height="978" alt="Screenshot (97)" src="https://github.com/user-attachments/assets/c921c471-ff02-4fdd-a248-17bd051335f8" />

<img width="1920" height="980" alt="Screenshot (98)" src="https://github.com/user-attachments/assets/2c229a82-35bd-433d-bcdd-75ecc77e8169" />

<img width="1920" height="980" alt="Screenshot (99)" src="https://github.com/user-attachments/assets/ba80d06f-23d1-491a-b254-3b491d0f3538" />


---

## Design Goals

The goal was not only to satisfy the assignment requirements but also to demonstrate software engineering practices that make the application easier to maintain and extend.

The architecture separates:

* API communication
* Business logic
* Validation
* Logging
* User interface

This separation allows additional order types or trading strategies to be added later without modifying the core client implementation.

---

## Prerequisites

* Python 3.10 or newer
* Binance Futures Testnet account
* Binance Futures Testnet API Key and Secret

Testnet URL:

https://testnet.binancefuture.com

---

## Installation

Clone the repository:

```bash
git clone https://github.com/Bhuvan1326/Trading-Bot.git
cd Trading-Bot
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Windows

```cmd
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file:

### Windows

```cmd
copy .env.example .env
```

### Linux/macOS

```bash
cp .env.example .env
```

Add your Binance Testnet credentials:

```env
API_KEY=your_api_key
API_SECRET=your_api_secret
```

---

## Configuration

| Variable                 | Required | Description                        |
| ------------------------ | -------- | ---------------------------------- |
| API_KEY                  | Yes      | Binance Futures Testnet API Key    |
| API_SECRET               | Yes      | Binance Futures Testnet API Secret |
| BINANCE_FUTURES_BASE_URL | No       | Binance Testnet base URL           |
| HTTP_TIMEOUT_SECONDS     | No       | HTTP request timeout               |
| API_MAX_RETRIES          | No       | Maximum retry attempts             |
| API_RETRY_BACKOFF_BASE   | No       | Base retry delay                   |

---

## Usage

### Check Futures Balance

```bash
python cli.py check-balance
```

### Place MARKET Order

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Place LIMIT Order

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000
```

### Place STOP_LIMIT Order

```bash
python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.001 --price 66500 --stop-price 67000
```

### Dry Run

Validate the order without sending it to Binance:

```bash
python cli.py place-order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 65000 --dry-run
```

### Order Status

```bash
python cli.py order-status --symbol BTCUSDT --order-id 123456789
```

### Interactive Mode

Launch the interactive prompt:

```bash
python cli.py
```

---

## Test Results

Successfully tested on Binance Futures Testnet.

| Feature           | Status   |
| ----------------- | -------- |
| Check Balance     | ✅ Tested |
| MARKET Orders     | ✅ Tested |
| LIMIT Orders      | ✅ Tested |
| STOP_LIMIT Orders | ✅ Tested |
| BUY Orders        | ✅ Tested |
| SELL Orders       | ✅ Tested |
| Logging           | ✅ Tested |
| Error Handling    | ✅ Tested |
| Dry Run           | ✅ Tested |

### Verified Testnet Results

#### Balance Retrieval

Successfully fetched Futures Testnet account balance.

#### Market Order

Successfully submitted and received a valid order response.

#### Limit Order

Successfully submitted and accepted by Binance Futures Testnet.

#### Stop-Limit Order

Successfully submitted using Binance Futures Algo Order endpoints.

Example response:

```text
algoId      1000000092863934
algoStatus  NEW
Order placed successfully
```

---

## Project Structure

```text
Trading-Bot/
├── bot/
│   ├── __init__.py
│   ├── client.py
│   ├── orders.py
│   ├── validators.py
│   ├── logging_config.py
│   └── config.py
├── cli.py
├── requirements.txt
├── README.md
├── .env.example
├── sample_logs/
└── logs/
```

---

## Logging

Application logs are written to:

```text
logs/trading_bot.log
```

Logged information includes:

* API requests
* API responses
* Validation failures
* Network failures
* Binance API errors
* Order placement summaries

Sensitive information such as API secrets and signatures is never logged.

Log rotation is enabled:

* Maximum size: 5 MB
* Backup files retained: 3

---

## Error Handling

The application gracefully handles:

* Invalid symbols
* Invalid sides
* Invalid order types
* Invalid quantities
* Missing prices
* Missing stop prices
* Missing API credentials
* Binance API errors
* Network failures
* Request timeouts

Errors are displayed using user-friendly CLI messages instead of raw Python tracebacks.

---

## Assumptions

* Binance Futures Testnet only
* USDT-M Futures only
* One-way position mode
* API credentials are provided through environment variables
* Retry logic applies only to network-related failures
* Stop-Limit orders are implemented using Binance Algo Order endpoints

---

## Bonus Features

* STOP_LIMIT Orders
* Dry-Run Mode
* Interactive CLI Mode
* Retry Logic with Exponential Backoff
* Rotating Log Files
* Centralized Configuration
* Rich Terminal Output
* Sample Log Files

---

## Submission Notes

This project fulfills all required assignment criteria and includes additional functionality demonstrating:

* Clean architecture
* Extensible design
* Production-style logging
* Robust error handling
* Practical API integration

---

## License

MIT License

This project is intended for educational, interview, and demonstration purposes only. It is not financial advice.
