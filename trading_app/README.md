# Trading System Application

This directory contains the Python trading application code that runs on AWS Lambda.

## Architecture

The application consists of:

- **Main Orchestrator** (`main.py`): Coordinates daily trading workflow
- **Kelly Factor Calculator** (`kelly_factor.py`): Calculates position sizing
- **Alpaca Connector** (`alpaca_connector.py`): Executes trades via Alpaca API
- **YFinance Connector** (`yfinance_connector.py`): Fetches historical market data

## Core Components

### Trading Orchestrator
- Coordinates the daily workflow
- Manages error handling and logging
- Sends notifications and stores results

### Kelly Factor Calculator
- Implements Kelly criterion for position sizing
- Analyzes historical data for risk assessment
- Provides optimal bet size calculations

### Market Data & Trading
- YFinance integration for historical data
- Alpaca API for live trading execution
- Real-time market analysis

## Configuration

Environment variables (set by CDK):
- `TRADING_TABLE_NAME`: DynamoDB table for transactions
- `DLQ_URL`: Dead letter queue for failed events
- `SNS_TOPIC_ARN`: SNS topic for notifications
- `SECRETS_ARN`: AWS Secrets Manager for API keys

## Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run tests:
   ```bash
   pytest tests/
   ```

3. Code formatting:
   ```bash
   black src/
   flake8 src/
   ```

## Deployment

The application is deployed via AWS CDK from the `infrastructure/` directory.

## Monitoring

- AWS CloudWatch for logging and metrics
- SNS notifications for alerts
- DynamoDB for transaction history