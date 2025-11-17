# 🧪 Trading System Test Suite

## Overview

Comprehensive unit and integration test suite for the TQQQ-focused trading system.

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── pytest.ini              # Pytest settings
├── __init__.py
├── unit/                    # Unit tests (isolated components)
│   ├── signals/
│   │   ├── test_base_signal.py        # BaseSignal abstract class tests
│   │   └── test_twelve_data_ema.py    # TwelveDataEMASignal tests
│   ├── connectors/
│   │   └── test_twelve_data.py        # TwelveDataConnector tests
│   ├── trading/
│   │   └── test_alpaca_trader.py      # AlpacaTrader tests
│   └── test_main.py         # Lambda handler tests
├── integration/             # Integration tests (component interactions)
│   └── test_trading_workflow.py       # End-to-end workflow tests
└── fixtures/                # Test data and utilities
    └── market_data.py       # Market data fixtures
```

## 🚀 Running Tests

### Quick Commands

```bash
# Run all tests
make test

# Run specific test types
make test-unit              # Unit tests only
make test-integration       # Integration tests only
make test-cov              # Tests with coverage report
make test-quick            # Fast tests (no coverage)

# Install dependencies
make install

# Clean test artifacts
make clean
```

### Direct pytest Commands

```bash
# All tests with verbose output
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/signals/test_base_signal.py -v

# Run specific test method
pytest tests/unit/signals/test_base_signal.py::TestBaseSignal::test_get_signal_type_bullish -v
```

### Using Test Runner Script

```bash
# Run comprehensive test suite
python run_tests.py
```

## 📊 Test Coverage

The test suite covers:

### ✅ **Unit Tests (90+ tests)**

#### **BaseSignal Class**
- Signal type determination logic (bullish/bearish/neutral)
- EMA crossover conditions
- Edge cases and boundary conditions

#### **TwelveDataEMASignal Class**  
- Signal analysis for single and multiple symbols
- Error handling for API failures
- Data validation and signal classification

#### **TwelveDataConnector Class**
- API key retrieval from Secrets Manager
- Stock data fetching and parsing
- EMA calculations
- Batch price retrieval
- Error handling for API failures

#### **AlpacaTrader Class**
- Account management
- Position tracking
- Buy/sell decision logic
- Order placement (buy/sell)
- Portfolio rebalancing strategy
- All-funds TQQQ buying logic
- Position liquidation

#### **Main Lambda Handler**
- Event processing
- Signal-to-trade workflow
- Error handling and logging
- Response formatting

### ✅ **Integration Tests**

#### **End-to-End Trading Workflow**
- Bullish signal → portfolio liquidation → TQQQ purchase
- Bearish signal → TQQQ sale (if position exists)
- Neutral signal → no action
- API error handling across components
- Complete data flow validation

### 📈 **Key Test Scenarios**

#### **Signal Generation**
- ✅ Bullish: Price > 10h EMA > 20h EMA
- ✅ Bearish: Price < 10h EMA < 20h EMA  
- ✅ Neutral: Mixed conditions
- ✅ No data/API errors

#### **Trading Logic**
- ✅ Bullish → Sell all positions except TQQQ → Buy TQQQ with all funds
- ✅ Bearish → Sell TQQQ if position exists
- ✅ Neutral → No trades
- ✅ Error conditions → Graceful handling

#### **API Integration**
- ✅ Twelve Data API calls (price, historical data)
- ✅ Alpaca API calls (account, positions, orders)
- ✅ AWS Secrets Manager integration
- ✅ Rate limiting and error responses

## 🎯 Test Quality Metrics

### **Code Coverage Target**: 85%+
- Unit tests: 95% coverage
- Integration tests: Key workflows covered
- Error paths: Exception handling tested

### **Test Types**
- **Unit Tests**: Fast, isolated, mocked dependencies
- **Integration Tests**: Component interactions, real API patterns
- **Fixtures**: Reusable test data and scenarios

### **Quality Checks**
- ✅ All critical paths tested
- ✅ Error conditions handled
- ✅ Edge cases covered
- ✅ Mocking for external dependencies
- ✅ Parametrized tests for multiple scenarios

## 🛠 Test Development Guidelines

### **Writing New Tests**

1. **Unit Tests**: Test single components in isolation
   ```python
   def test_specific_functionality(self):
       # Arrange
       component = ComponentClass()
       
       # Act  
       result = component.method(input_data)
       
       # Assert
       assert result.expected_property == expected_value
   ```

2. **Integration Tests**: Test component interactions
   ```python
   @patch('external.dependency')
   def test_workflow_integration(self, mock_dependency):
       # Test multiple components working together
   ```

3. **Use Fixtures**: Leverage shared test data
   ```python
   def test_with_fixture(self, mock_twelve_data_response):
       # Use pre-configured test data
   ```

### **Best Practices**

- ✅ **Mock external dependencies** (APIs, AWS services)
- ✅ **Test error conditions** not just happy paths
- ✅ **Use descriptive test names** that explain what's being tested
- ✅ **Keep tests focused** - one concept per test
- ✅ **Use parameterized tests** for multiple similar scenarios

## 🚦 CI/CD Integration

The test suite is designed for CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --cov=src --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## 📝 Test Maintenance

### **Regular Tasks**
- Update tests when adding new features
- Maintain test fixtures as data formats evolve
- Review and improve test coverage
- Update mocks when external APIs change

### **Performance**
- Unit tests: < 5 seconds total
- Integration tests: < 30 seconds total
- Full suite: < 1 minute

## 🎉 Benefits

✅ **Confidence**: Comprehensive test coverage ensures reliability  
✅ **Speed**: Fast feedback on changes  
✅ **Maintenance**: Easy to modify and extend  
✅ **Documentation**: Tests serve as living documentation  
✅ **Regression Protection**: Catches breaking changes early