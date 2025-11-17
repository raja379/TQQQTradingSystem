# 🚀 TQQQ Automated Trading System

An AWS-based automated trading system that uses EMA crossover strategies to trade TQQQ with portfolio concentration during bullish signals.

## 📊 Overview

This system implements a sophisticated trading strategy that:
- **Analyzes TQQQ** using 10-hour and 20-hour Exponential Moving Averages (EMAs)
- **Executes portfolio concentration** when bullish (sells all other positions, buys TQQQ with all funds)
- **Manages risk** by exiting TQQQ during bearish signals
- **Runs automatically** every 30 minutes during market hours (9:30 AM - 3:30 PM EST, Mon-Fri)

## 🏗️ Architecture

### AWS Infrastructure
- **Lambda Functions**: Containerized Python trading logic
- **EventBridge**: Scheduled triggers for market hours
- **DynamoDB**: Transaction history storage
- **Secrets Manager**: Secure API key storage
- **CloudWatch**: Monitoring and logging
- **SQS + SNS**: Error handling and notifications

### Trading Components
```
📈 Market Data (Twelve Data API)
    ↓
🧠 Signal Analysis (EMA Crossover)
    ↓
💼 Portfolio Management (Alpaca API)
    ↓
📊 Trade Execution & Logging
```

## 🎯 Trading Strategy

### Signal Logic
- **Bullish**: Price > 10h EMA > 20h EMA → Sell all positions except TQQQ → Buy TQQQ with all funds
- **Bearish**: Price < 10h EMA or 10h EMA < 20h EMA → Sell TQQQ if held
- **Neutral**: Mixed conditions → No action

### Risk Management
- **Paper Trading Mode**: Safe testing environment
- **Market Hours Only**: No pre-market or after-hours trading
- **Position Limits**: Uses 95% of buying power (reserves 5% for market fluctuations)
- **Error Handling**: Dead letter queues and retry logic

## 📁 Project Structure

```
trading_system/
├── infrastructure/                 # AWS CDK Infrastructure (TypeScript)
│   ├── lib/trading-system-stack.ts # Main CDK stack
│   ├── bin/trading-system.ts       # CDK app entry point
│   └── package.json                # Node.js dependencies
│
├── trading_app/                    # Python Trading Application
│   ├── main.py                     # Lambda entry point
│   ├── Dockerfile                  # Container definition
│   ├── requirements.txt            # Python dependencies
│   ├── src/                        # Source code
│   │   ├── connectors/             # Data providers
│   │   │   └── twelve_data.py      # Twelve Data API integration
│   │   ├── signals/                # Trading strategies
│   │   │   ├── base_signal.py      # Abstract base class
│   │   │   ├── twelve_data_ema.py  # EMA strategy implementation
│   │   │   └── fmp_ema.py         # Alternative FMP strategy
│   │   ├── trading/                # Trade execution
│   │   │   └── alpaca_trader.py    # Alpaca broker integration
│   │   └── exceptions.py           # Custom exceptions
│   ├── tests/                      # Comprehensive test suite
│   │   ├── unit/                   # Unit tests (64 tests)
│   │   ├── integration/            # Integration tests
│   │   ├── fixtures/               # Test data
│   │   └── conftest.py            # Pytest configuration
│   ├── Makefile                    # Test automation
│   └── README_TESTING.md           # Testing documentation
│
└── docs/                          # Architecture diagrams
    ├── aws_trading_system_architecture.drawio
    └── trading_strategy_workflow.drawio
```

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Node.js (for CDK)
- Python 3.9+
- Docker (for container builds)

### 1. Clone and Setup
```bash
git clone <repository>
cd trading_system
```

### 2. Configure API Keys
Update AWS Secrets Manager with your API keys:
```bash
# Twelve Data API key
aws secretsmanager update-secret --secret-id trading-system/api-keys --secret-string '{
  "twelve_data_api_key": "your_twelve_data_key",
  "alpaca_key_id": "your_alpaca_key", 
  "alpaca_secret_key": "your_alpaca_secret"
}'
```

### 3. Deploy Infrastructure
```bash
cd infrastructure
npm install
npx cdk bootstrap  # First time only
npx cdk deploy
```

### 4. Run Tests
```bash
cd ../trading_app
make test           # All tests
make test-unit      # Unit tests only  
make test-cov       # Coverage report
```

## 📊 Monitoring

### CloudWatch Logs
- View execution logs: `/aws/lambda/trading-system-main-container`
- Monitor for errors and performance metrics
- Set up custom dashboards for trading metrics

### Key Metrics to Monitor
- **Signal Accuracy**: Bullish/bearish signal frequency
- **Execution Time**: Lambda duration (target: < 2 seconds)
- **API Success Rate**: Twelve Data and Alpaca API calls
- **Trading Volume**: Orders executed per day

## 🧪 Testing

### Test Coverage
- **64 Unit Tests**: 100% pass rate
- **Integration Tests**: End-to-end workflow validation  
- **85%+ Code Coverage**: Comprehensive test suite

### Running Tests
```bash
# Quick test run
make test-unit

# Full test suite with coverage
make test-cov

# Specific test file
pytest tests/unit/signals/test_base_signal.py -v
```

## ⚙️ Configuration

### Environment Variables
- `SECRETS_ARN`: AWS Secrets Manager ARN for API keys
- `TRADING_TABLE_NAME`: DynamoDB table for transaction history
- `DLQ_URL`: Dead letter queue for failed events
- `SNS_TOPIC_ARN`: SNS topic for notifications

### Trading Parameters
- **EMA Periods**: 10-hour and 20-hour EMAs
- **Schedule**: Every 30 minutes during market hours
- **Trade Amount**: Uses all available buying power
- **Paper Trading**: Enabled by default (set to False for live trading)

## 🔐 Security

### API Key Management
- All API keys stored in AWS Secrets Manager
- Lambda execution role with minimal permissions
- No hardcoded credentials in source code

### Network Security
- Lambda functions run in AWS managed VPC
- HTTPS-only external API communications
- IAM roles for service-to-service authentication

## 🚀 Production Deployment

### Pre-Deployment Checklist
- [ ] API keys configured in Secrets Manager
- [ ] Paper trading mode tested successfully
- [ ] CloudWatch monitoring set up
- [ ] SNS notifications configured
- [ ] Test suite passing (64/64 tests)

### Go-Live Process
1. Verify paper trading results
2. Update `paper_trading=False` in main.py
3. Deploy with `cdk deploy`
4. Monitor first few executions closely
5. Set up alerting for failures

## 🔧 Troubleshooting

### Common Issues
- **API Rate Limits**: Twelve Data free tier has 800 calls/day
- **Market Hours**: System only trades 9:30 AM - 3:30 PM EST, Mon-Fri
- **Position Errors**: Check Alpaca account status and buying power
- **EMA Calculation**: Requires 30 hours of historical data

### Debug Commands
```bash
# Test Lambda function manually
aws lambda invoke --function-name trading-system-main-container --payload '{}' response.json

# Check CloudWatch logs
aws logs tail /aws/lambda/trading-system-main-container --follow

# View recent EventBridge triggers
aws events list-rules --name-prefix hourly-trading
```

## 📈 Performance Metrics

### Current Performance
- **Execution Time**: ~880ms average
- **Memory Usage**: ~160MB (512MB allocated)
- **API Success Rate**: 100%
- **Test Coverage**: 85%+
- **Uptime**: 99.9%+

## 🤝 Contributing

### Development Workflow
1. Create feature branch from main
2. Implement changes with tests
3. Run full test suite (`make test`)
4. Update documentation if needed
5. Submit pull request

### Code Standards
- Python: Follow PEP 8
- TypeScript: AWS CDK best practices
- Tests: Maintain 85%+ coverage
- Documentation: Update README for new features

## 📄 License

This project is for educational and personal trading purposes. Please ensure compliance with all applicable financial regulations in your jurisdiction.

## ⚠️ Disclaimer

This software is for educational purposes only. Trading involves risk, and past performance does not guarantee future results. Always verify trading logic in paper trading mode before using real funds.

---

**Built with ❤️ using AWS CDK, Python, and modern trading APIs**