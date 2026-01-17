# TQQQ Automated Trading System

## Summary

This codebase is an **AWS-based Automated Trading System** for executing a TQQQ-focused EMA crossover strategy.

### Core Purpose

The system automatically trades TQQQ (a 3x leveraged NASDAQ-100 ETF) using a technical analysis strategy based on Exponential Moving Averages. It runs every 30 minutes during market hours (9:30 AM - 3:30 PM EST) and makes concentrated portfolio decisions:

- **Bullish Signal** (Price > 10h EMA > 20h EMA): Liquidates entire portfolio and buys TQQQ with all available funds
- **Bearish Signal**: Sells TQQQ position if held
- **Neutral**: No action

### Architecture

- **Cloud Infrastructure**: AWS CDK (TypeScript) deploying Lambda, EventBridge, DynamoDB, Secrets Manager, CloudWatch
- **Trading Application**: Python containerized Lambda function
- **Data Sources**: Twelve Data API (primary) and Financial Modeling Prep API (fallback)
- **Broker**: Alpaca (supports paper trading mode)

### Key Components

- `trading_app/main.py` - Lambda handler orchestrating the workflow
- `src/signals/twelve_data_ema.py` - EMA crossover signal analysis
- `src/connectors/twelve_data.py` - Market data fetching and EMA calculations
- `src/trading/alpaca_trader.py` - Trade execution and portfolio management
- `infrastructure/` - AWS CDK infrastructure as code

### Testing & Quality

- 90+ unit tests with 85%+ code coverage
- Integration tests for end-to-end workflows
- Paper trading mode for safe testing
- Comprehensive error handling with dead letter queues

This is a production-ready, well-tested automated trading system designed for concentrated momentum trading based on technical indicators.

## Project Structure

```
trading_system/
├── trading_app/              # Main Lambda application
│   └── main.py              # Entry point and orchestration logic
│
├── src/                     # Core trading system modules
│   ├── connectors/         # External API integrations (market data)
│   ├── signals/            # Trading signal generation (EMA strategy)
│   ├── trading/            # Trade execution and portfolio management
│   └── utils/              # Shared utilities and helpers
│
├── infrastructure/          # AWS CDK infrastructure definitions
│   └── lib/                # CDK stack definitions
│
├── tests/                   # Test suite
│   ├── unit/               # Unit tests for individual components
│   └── integration/        # End-to-end workflow tests
│
├── config/                  # Configuration files
└── docs/                    # Documentation
```

## Development Notes

- Python 3.x for trading logic
- TypeScript for infrastructure (AWS CDK)
- Docker for Lambda containerization
- pytest for testing framework
