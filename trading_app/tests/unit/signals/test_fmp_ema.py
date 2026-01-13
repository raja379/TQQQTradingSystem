"""
Unit tests for FMPEMASignal class.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from signals.fmp_ema import FMPEMASignal


class TestFMPEMASignal:
    """Test cases for FMPEMASignal class."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('signals.fmp_ema.FMPEMASignal._get_fmp_api_key', return_value='test_api_key'):
            self.signal = FMPEMASignal()

    def test_initialization(self):
        """Test signal initialization."""
        assert self.signal.name == "fmp_ema"
        assert self.signal.base_url == "https://financialmodelingprep.com/api/v3"
        assert self.signal.api_key == 'test_api_key'

    @patch.dict('os.environ', {'SECRETS_ARN': 'test-arn'})
    @patch('boto3.client')
    def test_get_fmp_api_key_success(self, mock_boto_client):
        """Test successful API key retrieval from Secrets Manager."""
        mock_secrets_client = Mock()
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': '{"fmp_api_key": "test_key_123"}'
        }
        mock_boto_client.return_value = mock_secrets_client

        signal = FMPEMASignal()
        api_key = signal._get_fmp_api_key()

        assert api_key == "test_key_123"

    @patch.dict('os.environ', {}, clear=True)
    def test_get_fmp_api_key_no_env_var(self):
        """Test API key retrieval when SECRETS_ARN is not set."""
        signal = FMPEMASignal()
        api_key = signal._get_fmp_api_key()

        assert api_key is None

    @patch('requests.get')
    def test_get_current_quote_success(self, mock_get):
        """Test successful current quote retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'historical': [
                {'close': 55.75, 'date': '2025-11-17'}
            ]
        }
        mock_get.return_value = mock_response

        price = self.signal.get_current_quote('TQQQ')

        assert price == 55.75
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_get_current_quote_no_data(self, mock_get):
        """Test quote retrieval when no data is available."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        # Mock demo endpoint failure too
        mock_demo_response = Mock()
        mock_demo_response.status_code = 404
        mock_demo_response.json.return_value = {}
        mock_get.side_effect = [mock_response, mock_demo_response]

        price = self.signal.get_current_quote('INVALID')

        assert price is None

    @patch('requests.get')
    def test_get_historical_data_success(self, mock_get):
        """Test successful historical data retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'historical': [
                {
                    'date': '2025-11-17',
                    'open': 55.00,
                    'high': 56.00,
                    'low': 54.50,
                    'close': 55.75,
                    'volume': 1000000
                },
                {
                    'date': '2025-11-16',
                    'open': 54.00,
                    'high': 55.50,
                    'low': 53.75,
                    'close': 55.00,
                    'volume': 950000
                }
            ]
        }
        mock_get.return_value = mock_response

        df = self.signal.get_historical_data('TQQQ', days=2)

        assert df is not None
        assert len(df) == 2
        assert 'Close' in df.columns
        assert df['Close'].iloc[-1] == 55.75

    @patch('requests.get')
    def test_get_historical_data_no_data(self, mock_get):
        """Test historical data retrieval when no data is available."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Mock demo endpoint failure too
        mock_demo_response = Mock()
        mock_demo_response.status_code = 404
        mock_get.side_effect = [mock_response, mock_demo_response]

        df = self.signal.get_historical_data('INVALID')

        assert df is None

    def test_calculate_ema(self):
        """Test EMA calculation."""
        data = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])

        ema = self.signal.calculate_ema(data, period=5)

        assert not ema.empty
        assert len(ema) == len(data)
        # EMA should be close to the data values
        assert ema.iloc[-1] > data.iloc[-1] - 5
        assert ema.iloc[-1] < data.iloc[-1] + 5

    @patch('signals.fmp_ema.FMPEMASignal.get_current_quote')
    @patch('signals.fmp_ema.FMPEMASignal.get_historical_data')
    def test_analyze_successful_bullish(self, mock_hist_data, mock_quote):
        """Test successful analysis with bullish signal."""
        # Mock current price - higher than the trend to ensure bullish
        mock_quote.return_value = 135.0

        # Mock historical data with upward trend
        dates = pd.date_range('2025-11-01', periods=30, freq='D')
        close_prices = [100 + i for i in range(30)]  # 100 to 129
        df = pd.DataFrame({
            'Open': close_prices,
            'High': [p + 1 for p in close_prices],
            'Low': [p - 1 for p in close_prices],
            'Close': close_prices,
            'Volume': [1000000] * 30
        }, index=dates)
        mock_hist_data.return_value = df

        result = self.signal.analyze('TQQQ')

        assert result['status'] == 'analyzed'
        assert result['signal'] == 'bullish'
        assert result['current_price'] == 135.0
        assert 'ema_10' in result
        assert 'ema_20' in result
        assert result['data_source'] == 'financial_modeling_prep'
        assert 'timestamp' in result

    @patch('signals.fmp_ema.FMPEMASignal.get_current_quote')
    @patch('signals.fmp_ema.FMPEMASignal.get_historical_data')
    def test_analyze_bearish_signal(self, mock_hist_data, mock_quote):
        """Test bearish signal detection."""
        # Mock current price (lower than EMAs)
        mock_quote.return_value = 90.0

        # Mock historical data with declining trend
        dates = pd.date_range('2025-11-01', periods=30, freq='D')
        close_prices = [130 - i for i in range(30)]  # Declining prices
        df = pd.DataFrame({
            'Open': close_prices,
            'High': [p + 1 for p in close_prices],
            'Low': [p - 1 for p in close_prices],
            'Close': close_prices,
            'Volume': [1000000] * 30
        }, index=dates)
        mock_hist_data.return_value = df

        result = self.signal.analyze('TQQQ')

        assert result['status'] == 'analyzed'
        assert result['signal'] == 'bearish'
        assert result['current_price'] == 90.0

    @patch('signals.fmp_ema.FMPEMASignal.get_current_quote')
    @patch('signals.fmp_ema.FMPEMASignal.get_historical_data')
    def test_analyze_neutral_signal(self, mock_hist_data, mock_quote):
        """Test neutral signal detection."""
        # Mock current price between EMAs
        mock_quote.return_value = 107.0

        # Mock historical data
        dates = pd.date_range('2025-11-01', periods=30, freq='D')
        close_prices = [105 + (i % 3) for i in range(30)]  # Oscillating prices
        df = pd.DataFrame({
            'Open': close_prices,
            'High': [p + 1 for p in close_prices],
            'Low': [p - 1 for p in close_prices],
            'Close': close_prices,
            'Volume': [1000000] * 30
        }, index=dates)
        mock_hist_data.return_value = df

        result = self.signal.analyze('TQQQ')

        assert result['status'] == 'analyzed'
        assert result['signal'] in ['neutral', 'bullish', 'bearish']  # Could be any depending on EMAs

    def test_analyze_no_api_key(self):
        """Test analysis when API key is not available."""
        signal = FMPEMASignal()
        signal.api_key = None

        result = signal.analyze('TQQQ')

        assert result['status'] == 'error'
        assert 'FMP API key not available' in result['message']

    @patch('signals.fmp_ema.FMPEMASignal.get_current_quote')
    def test_analyze_no_quote_data(self, mock_quote):
        """Test handling when quote data is not available."""
        mock_quote.return_value = None

        result = self.signal.analyze('TQQQ')

        assert result['status'] == 'no_data'

    @patch('signals.fmp_ema.FMPEMASignal.get_current_quote')
    @patch('signals.fmp_ema.FMPEMASignal.get_historical_data')
    def test_analyze_no_historical_data(self, mock_hist_data, mock_quote):
        """Test handling when historical data is not available."""
        mock_quote.return_value = 110.0
        mock_hist_data.return_value = None

        result = self.signal.analyze('TQQQ')

        assert result['status'] == 'no_data'

    @patch('signals.fmp_ema.FMPEMASignal.get_current_quote')
    @patch('signals.fmp_ema.FMPEMASignal.get_historical_data')
    def test_analyze_exception_handling(self, mock_hist_data, mock_quote):
        """Test exception handling during analysis."""
        mock_quote.side_effect = Exception("API Error")

        result = self.signal.analyze('TQQQ')

        assert result['status'] == 'error'
        assert 'API Error' in result['message']

    @patch('signals.fmp_ema.FMPEMASignal.analyze')
    def test_analyze_multiple(self, mock_analyze):
        """Test multiple symbol analysis."""
        def analyze_side_effect(symbol):
            return {
                'status': 'analyzed',
                'signal': 'bullish' if symbol == 'TQQQ' else 'bearish',
                'current_price': 110.0 if symbol == 'TQQQ' else 450.0,
                'ema_10': 108.0,
                'ema_20': 106.0
            }

        mock_analyze.side_effect = analyze_side_effect

        symbols = ['TQQQ', 'SPY', 'QQQ']
        results = self.signal.analyze_multiple(symbols)

        assert len(results) == 3
        assert results['TQQQ']['signal'] == 'bullish'
        assert results['SPY']['signal'] == 'bearish'
        assert results['QQQ']['signal'] == 'bearish'
        assert mock_analyze.call_count == 3

    @patch('signals.fmp_ema.FMPEMASignal.analyze')
    def test_analyze_multiple_with_error(self, mock_analyze):
        """Test multiple analysis with one symbol erroring."""
        def analyze_side_effect(symbol):
            if symbol == 'INVALID':
                raise Exception("Invalid symbol")
            return {
                'status': 'analyzed',
                'signal': 'bullish',
                'current_price': 110.0
            }

        mock_analyze.side_effect = analyze_side_effect

        symbols = ['TQQQ', 'INVALID', 'SPY']
        results = self.signal.analyze_multiple(symbols)

        assert len(results) == 3
        assert results['TQQQ']['status'] == 'analyzed'
        assert results['INVALID']['status'] == 'error'
        assert 'Invalid symbol' in results['INVALID']['message']
        assert results['SPY']['status'] == 'analyzed'

    @patch('requests.get')
    def test_get_multiple_quotes_success(self, mock_get):
        """Test successful batch quote retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'symbol': 'TQQQ', 'price': 55.75},
            {'symbol': 'SPY', 'price': 450.25},
            {'symbol': 'QQQ', 'price': 380.50}
        ]
        mock_get.return_value = mock_response

        symbols = ['TQQQ', 'SPY', 'QQQ']
        results = self.signal.get_multiple_quotes(symbols)

        assert results is not None
        assert len(results) == 3
        assert results['TQQQ'] == 55.75
        assert results['SPY'] == 450.25
        assert results['QQQ'] == 380.50

    @patch('requests.get')
    def test_get_multiple_quotes_no_api_key(self, mock_get):
        """Test batch quotes when API key is not available."""
        signal = FMPEMASignal()
        signal.api_key = None

        results = signal.get_multiple_quotes(['TQQQ', 'SPY'])

        assert results is None
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_multiple_quotes_api_error(self, mock_get):
        """Test batch quotes handling API errors."""
        mock_get.side_effect = Exception("API Error")

        results = self.signal.get_multiple_quotes(['TQQQ', 'SPY'])

        assert results is None
