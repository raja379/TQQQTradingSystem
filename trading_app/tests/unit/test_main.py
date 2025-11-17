"""
Unit tests for main Lambda handler.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@patch('main.TwelveDataEMASignal')
@patch('main.AlpacaTrader')
def test_handler_success(mock_alpaca_trader, mock_signal_analyzer):
    """Test successful Lambda handler execution."""
    # Import here to avoid issues with patching
    import main
    
    # Mock signal analyzer
    mock_analyzer = Mock()
    mock_analyzer.analyze_multiple.return_value = {
        'TQQQ': {
            'status': 'analyzed',
            'signal': 'bullish',
            'current_price': 110.0,
            'ema_10': 108.0,
            'ema_20': 106.0
        }
    }
    mock_signal_analyzer.return_value = mock_analyzer
    
    # Mock trader
    mock_trader = Mock()
    mock_trader.process_all_stocks.return_value = {
        'account_status': 'ACTIVE',
        'buying_power': 197994.15,
        'total_orders': 1,
        'buys': 1,
        'sells': 0,
        'orders': []
    }
    mock_alpaca_trader.return_value = mock_trader
    
    # Test event
    event = {'source': 'aws.events'}
    context = Mock()
    
    # Execute handler
    result = main.handler(event, context)
    
    # Assertions
    assert result['statusCode'] == 200
    
    body = json.loads(result['body'])
    assert body['message'] == 'Trading execution completed'
    assert 'timestamp' in body
    assert body['watchlist'] == ['TQQQ']
    assert body['signal_summary']['bullish'] == 1
    assert 'detailed_signals' in body
    assert 'trading_results' in body
    
    # Verify mocks were called
    mock_signal_analyzer.assert_called_once()
    mock_analyzer.analyze_multiple.assert_called_once_with(['TQQQ'])
    mock_alpaca_trader.assert_called_once_with(paper_trading=True)
    mock_trader.process_all_stocks.assert_called_once()


@patch('main.TwelveDataEMASignal')
@patch('main.AlpacaTrader')
def test_handler_bearish_signal(mock_alpaca_trader, mock_signal_analyzer):
    """Test handler with bearish signal."""
    import main
    
    # Mock bearish signal
    mock_analyzer = Mock()
    mock_analyzer.analyze_multiple.return_value = {
        'TQQQ': {
            'status': 'analyzed',
            'signal': 'bearish',
            'current_price': 104.0,
            'ema_10': 106.0,
            'ema_20': 108.0
        }
    }
    mock_signal_analyzer.return_value = mock_analyzer
    
    # Mock trader with no trades
    mock_trader = Mock()
    mock_trader.process_all_stocks.return_value = {
        'account_status': 'ACTIVE',
        'buying_power': 197994.15,
        'total_orders': 0,
        'buys': 0,
        'sells': 0,
        'orders': []
    }
    mock_alpaca_trader.return_value = mock_trader
    
    event = {}
    context = Mock()
    
    result = main.handler(event, context)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['signal_summary']['bearish'] == 1
    assert body['signal_summary']['bullish'] == 0


@patch('main.TwelveDataEMASignal')
def test_handler_signal_analyzer_exception(mock_signal_analyzer):
    """Test handler when signal analyzer raises exception."""
    import main
    
    # Mock signal analyzer to raise exception
    mock_signal_analyzer.side_effect = Exception("API connection failed")
    
    event = {}
    context = Mock()
    
    result = main.handler(event, context)
    
    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert 'error' in body
    assert 'API connection failed' in body['error']
    assert 'timestamp' in body


@patch('main.TwelveDataEMASignal')
@patch('main.AlpacaTrader')
def test_handler_trader_exception(mock_alpaca_trader, mock_signal_analyzer):
    """Test handler when trader raises exception."""
    import main
    
    # Mock successful signal analysis
    mock_analyzer = Mock()
    mock_analyzer.analyze_multiple.return_value = {
        'TQQQ': {
            'status': 'analyzed',
            'signal': 'bullish',
            'current_price': 110.0
        }
    }
    mock_signal_analyzer.return_value = mock_analyzer
    
    # Mock trader to raise exception
    mock_alpaca_trader.side_effect = Exception("Trading API unavailable")
    
    event = {}
    context = Mock()
    
    result = main.handler(event, context)
    
    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert 'error' in body
    assert 'Trading API unavailable' in body['error']


@patch('main.TwelveDataEMASignal')
@patch('main.AlpacaTrader')
def test_handler_signal_summary_calculation(mock_alpaca_trader, mock_signal_analyzer):
    """Test signal summary calculation with mixed signals."""
    import main
    
    # Mock mixed signals
    mock_analyzer = Mock()
    mock_analyzer.analyze_multiple.return_value = {
        'TQQQ': {
            'status': 'analyzed',
            'signal': 'neutral',
            'current_price': 107.0,
            'ema_10': 106.0,
            'ema_20': 108.0
        }
    }
    mock_signal_analyzer.return_value = mock_analyzer
    
    mock_trader = Mock()
    mock_trader.process_all_stocks.return_value = {
        'total_orders': 0,
        'buys': 0,
        'sells': 0
    }
    mock_alpaca_trader.return_value = mock_trader
    
    event = {}
    context = Mock()
    
    result = main.handler(event, context)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['signal_summary']['neutral'] == 1
    assert body['signal_summary']['bullish'] == 0
    assert body['signal_summary']['bearish'] == 0
    assert body['signal_summary']['no_data'] == 0


@patch('main.TwelveDataEMASignal')
@patch('main.AlpacaTrader')
def test_handler_no_data_signal(mock_alpaca_trader, mock_signal_analyzer):
    """Test handler with no data signal."""
    import main
    
    # Mock no data signal
    mock_analyzer = Mock()
    mock_analyzer.analyze_multiple.return_value = {
        'TQQQ': {
            'status': 'no_data'
        }
    }
    mock_signal_analyzer.return_value = mock_analyzer
    
    mock_trader = Mock()
    mock_trader.process_all_stocks.return_value = {
        'total_orders': 0,
        'buys': 0,
        'sells': 0
    }
    mock_alpaca_trader.return_value = mock_trader
    
    event = {}
    context = Mock()
    
    result = main.handler(event, context)
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['signal_summary']['no_data'] == 1


@patch('main.logger')
@patch('main.TwelveDataEMASignal')
@patch('main.AlpacaTrader')
def test_handler_logging(mock_alpaca_trader, mock_signal_analyzer, mock_logger):
    """Test that handler logs appropriately."""
    import main
    
    # Mock successful execution
    mock_analyzer = Mock()
    mock_analyzer.analyze_multiple.return_value = {
        'TQQQ': {'status': 'analyzed', 'signal': 'bullish'}
    }
    mock_signal_analyzer.return_value = mock_analyzer
    
    mock_trader = Mock()
    mock_trader.process_all_stocks.return_value = {
        'total_orders': 1,
        'buys': 1,
        'sells': 0
    }
    mock_alpaca_trader.return_value = mock_trader
    
    event = {'test': 'event'}
    context = Mock()
    
    main.handler(event, context)
    
    # Verify logging calls
    mock_logger.info.assert_any_call('Analyzing market signals for watchlist: [\'TQQQ\']')
    mock_logger.info.assert_any_call('Executing TQQQ-focused strategy via Alpaca')
    
    # Check final log message
    final_log_calls = [call for call in mock_logger.info.call_args_list 
                      if 'Trading execution complete' in str(call)]
    assert len(final_log_calls) > 0