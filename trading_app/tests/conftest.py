"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
import sys
from unittest.mock import Mock, MagicMock
import pandas as pd
from datetime import datetime

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def mock_twelve_data_response():
    """Mock response from Twelve Data API."""
    return {
        'values': [
            {
                'datetime': '2025-11-17 15:30:00',
                'open': '105.00',
                'high': '105.50',
                'low': '104.80',
                'close': '105.20',
                'volume': '1000000'
            },
            {
                'datetime': '2025-11-17 14:30:00', 
                'open': '104.50',
                'high': '105.20',
                'low': '104.30',
                'close': '105.00',
                'volume': '950000'
            },
            {
                'datetime': '2025-11-17 13:30:00',
                'open': '104.00',
                'high': '104.80',
                'low': '103.90',
                'close': '104.50',
                'volume': '800000'
            }
        ],
        'status': 'ok'
    }


@pytest.fixture
def mock_price_response():
    """Mock price response from Twelve Data API."""
    return {
        'price': '104.74'
    }


@pytest.fixture
def sample_price_data():
    """Sample price data for testing EMAs."""
    dates = pd.date_range('2025-11-01', periods=30, freq='H')
    prices = [100 + i * 0.5 + (i % 5) * 0.2 for i in range(30)]
    return pd.Series(prices, index=dates)


@pytest.fixture
def mock_alpaca_account():
    """Mock Alpaca account response."""
    return {
        'status': 'ACTIVE',
        'buying_power': '197994.15',
        'cash': '197994.15',
        'portfolio_value': '200000.00',
        'equity': '200000.00'
    }


@pytest.fixture
def mock_alpaca_position():
    """Mock Alpaca position response."""
    return {
        'symbol': 'TQQQ',
        'qty': '100',
        'avg_entry_price': '104.50',
        'market_value': '10474.00',
        'cost_basis': '10450.00',
        'unrealized_pl': '24.00'
    }


@pytest.fixture
def mock_alpaca_order():
    """Mock Alpaca order response."""
    return {
        'id': 'order-123456',
        'symbol': 'TQQQ',
        'qty': '100',
        'side': 'buy',
        'order_type': 'market',
        'status': 'new',
        'submitted_at': datetime.now().isoformat(),
        'filled_at': None,
        'filled_qty': '0'
    }


@pytest.fixture
def mock_secrets_manager():
    """Mock AWS Secrets Manager response."""
    return {
        'SecretString': '''{
            "twelve_data_api_key": "mock_twelve_data_key",
            "alpaca_key_id": "mock_alpaca_key",
            "alpaca_secret_key": "mock_alpaca_secret",
            "fmp_api_key": "mock_fmp_key"
        }'''
    }


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv('SECRETS_ARN', 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret')
    monkeypatch.setenv('TRADING_TABLE_NAME', 'test-trading-table')
    monkeypatch.setenv('DLQ_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/test-dlq')
    monkeypatch.setenv('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:test-topic')