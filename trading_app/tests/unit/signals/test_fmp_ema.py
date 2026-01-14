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

    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def setup_method(self, method, mock_get_key):
        """Set up test fixtures."""
        mock_get_key.return_value = 'test_api_key'
        self.signal = FMPEMASignal()

    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_initialization(self, mock_get_key):
        """Test signal initialization."""
        mock_get_key.return_value = 'test_api_key'
        signal = FMPEMASignal()

        assert signal.name == "fmp_ema"
        assert signal.api_key == 'test_api_key'
        assert signal.base_url == "https://financialmodelingprep.com/api/v3"

    @patch('boto3.client')
    def test_get_fmp_api_key_success(self, mock_boto_client):
        """Test successful API key retrieval from Secrets Manager."""
        mock_secrets_client = Mock()
        mock_boto_client.return_value = mock_secrets_client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': '{"fmp_api_key": "my_secret_key"}'
        }

        with patch.dict('os.environ', {'SECRETS_ARN': 'arn:aws:secretsmanager:test'}):
            signal = FMPEMASignal()
            assert signal.api_key == 'my_secret_key'

    @patch('boto3.client')
    def test_get_fmp_api_key_no_secrets_arn(self, mock_boto_client):
        """Test API key retrieval when SECRETS_ARN is not set."""
        with patch.dict('os.environ', {}, clear=True):
            signal = FMPEMASignal()
            assert signal.api_key is None

    @patch('boto3.client')
    def test_get_fmp_api_key_missing_key(self, mock_boto_client):
        """Test API key retrieval when key is not in secrets."""
        mock_secrets_client = Mock()
        mock_boto_client.return_value = mock_secrets_client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': '{"other_key": "value"}'
        }

        with patch.dict('os.environ', {'SECRETS_ARN': 'arn:aws:secretsmanager:test'}):
            signal = FMPEMASignal()
            assert signal.api_key is None

    @patch('boto3.client')
    def test_get_fmp_api_key_exception(self, mock_boto_client):
        """Test API key retrieval when exception occurs."""
        mock_boto_client.side_effect = Exception("Connection error")

        with patch.dict('os.environ', {'SECRETS_ARN': 'arn:aws:secretsmanager:test'}):
            signal = FMPEMASignal()
            assert signal.api_key is None

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_current_quote_success(self, mock_get_key, mock_requests_get):
        """Test successful quote retrieval."""
        mock_get_key.return_value = 'test_api_key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'historical': [{'close': 55.10}]
        }
        mock_requests_get.return_value = mock_response

        signal = FMPEMASignal()
        price = signal.get_current_quote('TQQQ')

        assert price == 55.10

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_current_quote_no_api_key(self, mock_get_key, mock_requests_get):
        """Test quote retrieval when API key is not available."""
        mock_get_key.return_value = None

        signal = FMPEMASignal()
        price = signal.get_current_quote('TQQQ')

        assert price is None

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_current_quote_fallback_to_demo(self, mock_get_key, mock_requests_get):
        """Test quote retrieval falls back to demo endpoint."""
        mock_get_key.return_value = 'test_api_key'

        # First call fails (main endpoint)
        mock_response_fail = Mock()
        mock_response_fail.status_code = 200
        mock_response_fail.json.return_value = {}

        # Second call succeeds (demo endpoint)
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [{'price': 55.50}]

        mock_requests_get.side_effect = [mock_response_fail, mock_response_success]

        signal = FMPEMASignal()
        price = signal.get_current_quote('TQQQ')

        assert price == 55.50

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_current_quote_exception(self, mock_get_key, mock_requests_get):
        """Test quote retrieval when exception occurs."""
        mock_get_key.return_value = 'test_api_key'
        mock_requests_get.side_effect = Exception("Network error")

        signal = FMPEMASignal()
        price = signal.get_current_quote('TQQQ')

        assert price is None

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_historical_data_success(self, mock_get_key, mock_requests_get):
        """Test successful historical data retrieval."""
        mock_get_key.return_value = 'test_api_key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'historical': [
                {'date': '2025-01-13', 'open': 55.0, 'high': 56.0, 'low': 54.0, 'close': 55.5, 'volume': 1000000},
                {'date': '2025-01-12', 'open': 54.0, 'high': 55.0, 'low': 53.0, 'close': 54.5, 'volume': 900000},
            ]
        }
        mock_requests_get.return_value = mock_response

        signal = FMPEMASignal()
        df = signal.get_historical_data('TQQQ', days=2)

        assert df is not None
        assert len(df) == 2
        assert 'Close' in df.columns
        assert 'Open' in df.columns

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_historical_data_no_api_key(self, mock_get_key, mock_requests_get):
        """Test historical data retrieval when API key is not available."""
        mock_get_key.return_value = None

        signal = FMPEMASignal()
        df = signal.get_historical_data('TQQQ')

        assert df is None

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_historical_data_exception(self, mock_get_key, mock_requests_get):
        """Test historical data retrieval when exception occurs."""
        mock_get_key.return_value = 'test_api_key'
        mock_requests_get.side_effect = Exception("API error")

        signal = FMPEMASignal()
        df = signal.get_historical_data('TQQQ')

        assert df is None

    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_calculate_ema(self, mock_get_key):
        """Test EMA calculation."""
        mock_get_key.return_value = 'test_api_key'
        signal = FMPEMASignal()

        data = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        ema = signal.calculate_ema(data, 5)

        assert len(ema) == len(data)
        assert not ema.empty

    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_calculate_ema_empty_series(self, mock_get_key):
        """Test EMA calculation with empty series."""
        mock_get_key.return_value = 'test_api_key'
        signal = FMPEMASignal()

        data = pd.Series([])
        ema = signal.calculate_ema(data, 5)

        assert len(ema) == 0

    @patch.object(FMPEMASignal, 'calculate_ema')
    @patch.object(FMPEMASignal, 'get_current_quote')
    @patch.object(FMPEMASignal, 'get_historical_data')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_bullish_signal(self, mock_get_key, mock_get_historical, mock_get_quote, mock_calc_ema):
        """Test bullish signal detection."""
        mock_get_key.return_value = 'test_api_key'
        # Bullish: price > ema_10 > ema_20
        mock_get_quote.return_value = 110.0

        dates = pd.date_range('2025-01-01', periods=30, freq='D')
        mock_get_historical.return_value = pd.DataFrame({
            'Close': [100.0] * 30
        }, index=dates)

        # Mock EMA calculations: ema_10=105, ema_20=100 -> price(110) > ema_10(105) > ema_20(100)
        mock_calc_ema.side_effect = [
            pd.Series([105.0] * 30),  # ema_10
            pd.Series([100.0] * 30)   # ema_20
        ]

        signal = FMPEMASignal()
        result = signal.analyze('TQQQ')

        assert result['status'] == 'analyzed'
        assert result['signal'] == 'bullish'
        assert result['current_price'] == 110.0
        assert result['data_source'] == 'financial_modeling_prep'

    @patch.object(FMPEMASignal, 'calculate_ema')
    @patch.object(FMPEMASignal, 'get_current_quote')
    @patch.object(FMPEMASignal, 'get_historical_data')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_bearish_signal(self, mock_get_key, mock_get_historical, mock_get_quote, mock_calc_ema):
        """Test bearish signal detection."""
        mock_get_key.return_value = 'test_api_key'
        # Bearish: price < ema_10 < ema_20
        mock_get_quote.return_value = 90.0

        dates = pd.date_range('2025-01-01', periods=30, freq='D')
        mock_get_historical.return_value = pd.DataFrame({
            'Close': [100.0] * 30
        }, index=dates)

        # Mock EMA calculations: ema_10=95, ema_20=100 -> price(90) < ema_10(95) < ema_20(100)
        mock_calc_ema.side_effect = [
            pd.Series([95.0] * 30),   # ema_10
            pd.Series([100.0] * 30)   # ema_20
        ]

        signal = FMPEMASignal()
        result = signal.analyze('TQQQ')

        assert result['status'] == 'analyzed'
        assert result['signal'] == 'bearish'

    @patch.object(FMPEMASignal, 'get_current_quote')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_no_data(self, mock_get_key, mock_get_quote):
        """Test handling when no quote data is returned."""
        mock_get_key.return_value = 'test_api_key'
        mock_get_quote.return_value = None

        signal = FMPEMASignal()
        result = signal.analyze('TQQQ')

        assert result['status'] == 'no_data'

    @patch.object(FMPEMASignal, 'get_current_quote')
    @patch.object(FMPEMASignal, 'get_historical_data')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_no_historical_data(self, mock_get_key, mock_get_historical, mock_get_quote):
        """Test handling when no historical data is returned."""
        mock_get_key.return_value = 'test_api_key'
        mock_get_quote.return_value = 55.0
        mock_get_historical.return_value = None

        signal = FMPEMASignal()
        result = signal.analyze('TQQQ')

        assert result['status'] == 'no_data'

    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_no_api_key(self, mock_get_key):
        """Test analyze when API key is not available."""
        mock_get_key.return_value = None

        signal = FMPEMASignal()
        result = signal.analyze('TQQQ')

        assert result['status'] == 'error'
        assert 'API key not available' in result['message']

    @patch.object(FMPEMASignal, 'get_current_quote')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_exception_handling(self, mock_get_key, mock_get_quote):
        """Test exception handling during analysis."""
        mock_get_key.return_value = 'test_api_key'
        mock_get_quote.side_effect = Exception("API Error")

        signal = FMPEMASignal()
        result = signal.analyze('TQQQ')

        assert result['status'] == 'error'
        assert 'API Error' in result['message']

    @patch.object(FMPEMASignal, 'analyze')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_multiple(self, mock_get_key, mock_analyze):
        """Test multiple symbol analysis."""
        mock_get_key.return_value = 'test_api_key'

        def analyze_side_effect(symbol):
            return {
                'status': 'analyzed',
                'signal': 'bullish' if symbol == 'TQQQ' else 'bearish',
                'current_price': 55.0
            }

        mock_analyze.side_effect = analyze_side_effect

        signal = FMPEMASignal()
        symbols = ['TQQQ', 'SPY']
        results = signal.analyze_multiple(symbols)

        assert len(results) == 2
        assert results['TQQQ']['signal'] == 'bullish'
        assert results['SPY']['signal'] == 'bearish'

    @patch.object(FMPEMASignal, 'analyze')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_analyze_multiple_with_error(self, mock_get_key, mock_analyze):
        """Test multiple analysis with one symbol erroring."""
        mock_get_key.return_value = 'test_api_key'

        def analyze_side_effect(symbol):
            if symbol == 'INVALID':
                raise Exception("Invalid symbol")
            return {
                'status': 'analyzed',
                'signal': 'bullish',
                'current_price': 55.0
            }

        mock_analyze.side_effect = analyze_side_effect

        signal = FMPEMASignal()
        symbols = ['TQQQ', 'INVALID']
        results = signal.analyze_multiple(symbols)

        assert len(results) == 2
        assert results['TQQQ']['status'] == 'analyzed'
        assert results['INVALID']['status'] == 'error'

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_multiple_quotes_success(self, mock_get_key, mock_requests_get):
        """Test batch quote retrieval."""
        mock_get_key.return_value = 'test_api_key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'symbol': 'TQQQ', 'price': 55.10},
            {'symbol': 'SPY', 'price': 450.25}
        ]
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        signal = FMPEMASignal()
        quotes = signal.get_multiple_quotes(['TQQQ', 'SPY'])

        assert quotes is not None
        assert quotes['TQQQ'] == 55.10
        assert quotes['SPY'] == 450.25

    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_multiple_quotes_no_api_key(self, mock_get_key):
        """Test batch quote retrieval when API key is not available."""
        mock_get_key.return_value = None

        signal = FMPEMASignal()
        quotes = signal.get_multiple_quotes(['TQQQ', 'SPY'])

        assert quotes is None

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_multiple_quotes_empty_response(self, mock_get_key, mock_requests_get):
        """Test batch quote retrieval with empty response."""
        mock_get_key.return_value = 'test_api_key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        signal = FMPEMASignal()
        quotes = signal.get_multiple_quotes(['TQQQ'])

        assert quotes is None

    @patch('requests.get')
    @patch.object(FMPEMASignal, '_get_fmp_api_key')
    def test_get_multiple_quotes_exception(self, mock_get_key, mock_requests_get):
        """Test batch quote retrieval when exception occurs."""
        mock_get_key.return_value = 'test_api_key'
        mock_requests_get.side_effect = Exception("Network error")

        signal = FMPEMASignal()
        quotes = signal.get_multiple_quotes(['TQQQ'])

        assert quotes is None
