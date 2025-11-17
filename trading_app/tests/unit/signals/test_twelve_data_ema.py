"""
Unit tests for TwelveDataEMASignal class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from signals.twelve_data_ema import TwelveDataEMASignal


class TestTwelveDataEMASignal:
    """Test cases for TwelveDataEMASignal class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.signal = TwelveDataEMASignal()
    
    def test_initialization(self):
        """Test signal initialization."""
        assert self.signal.name == "twelve_data_ema"
        assert hasattr(self.signal, 'connector')
    
    @patch('connectors.twelve_data.TwelveDataConnector.get_stock_indicators')
    def test_analyze_successful(self, mock_get_indicators):
        """Test successful signal analysis."""
        # Mock the connector response
        mock_get_indicators.return_value = {
            'symbol': 'TQQQ',
            'current_price': 104.74,
            'ema_10': 105.72,
            'ema_20': 106.93,
            'timestamp': '2025-11-17T01:00:00'
        }
        
        result = self.signal.analyze('TQQQ')
        
        assert result['status'] == 'analyzed'
        assert result['signal'] == 'bearish'  # 104.74 < 105.72 < 106.93
        assert result['current_price'] == 104.74
        assert result['ema_10'] == 105.72
        assert result['ema_20'] == 106.93
        assert result['ema_spread'] == pytest.approx(105.72 - 106.93, rel=1e-6)
        assert result['data_source'] == 'twelve_data'
        assert 'timestamp' in result
    
    @patch('connectors.twelve_data.TwelveDataConnector.get_stock_indicators')
    def test_analyze_bullish_signal(self, mock_get_indicators):
        """Test bullish signal detection."""
        mock_get_indicators.return_value = {
            'symbol': 'TQQQ',
            'current_price': 110.0,
            'ema_10': 108.0,
            'ema_20': 106.0,
            'timestamp': '2025-11-17T01:00:00'
        }
        
        result = self.signal.analyze('TQQQ')
        
        assert result['signal'] == 'bullish'
        assert result['ema_spread'] == 2.0  # 108.0 - 106.0
    
    @patch('connectors.twelve_data.TwelveDataConnector.get_stock_indicators')
    def test_analyze_neutral_signal(self, mock_get_indicators):
        """Test neutral signal detection."""
        mock_get_indicators.return_value = {
            'symbol': 'TQQQ',
            'current_price': 107.0,
            'ema_10': 108.0,
            'ema_20': 106.0,
            'timestamp': '2025-11-17T01:00:00'
        }
        
        result = self.signal.analyze('TQQQ')
        
        assert result['signal'] == 'neutral'
    
    @patch('connectors.twelve_data.TwelveDataConnector.get_stock_indicators')
    def test_analyze_no_data(self, mock_get_indicators):
        """Test handling when no data is returned."""
        mock_get_indicators.return_value = None
        
        result = self.signal.analyze('TQQQ')
        
        assert result['status'] == 'no_data'
    
    @patch('connectors.twelve_data.TwelveDataConnector.get_stock_indicators')
    def test_analyze_insufficient_data(self, mock_get_indicators):
        """Test handling when data is incomplete."""
        mock_get_indicators.return_value = {
            'symbol': 'TQQQ',
            'current_price': 104.74,
            'ema_10': None,  # Missing EMA data
            'ema_20': 106.93,
            'timestamp': '2025-11-17T01:00:00'
        }
        
        result = self.signal.analyze('TQQQ')
        
        assert result['status'] == 'insufficient_data'
    
    @patch('connectors.twelve_data.TwelveDataConnector.get_stock_indicators')
    def test_analyze_exception_handling(self, mock_get_indicators):
        """Test exception handling during analysis."""
        mock_get_indicators.side_effect = Exception("API Error")
        
        result = self.signal.analyze('TQQQ')
        
        assert result['status'] == 'error'
        assert 'API Error' in result['message']
    
    @patch('signals.twelve_data_ema.TwelveDataEMASignal.analyze')
    def test_analyze_multiple(self, mock_analyze):
        """Test multiple symbol analysis."""
        # Mock individual analyze calls
        def analyze_side_effect(symbol):
            return {
                'status': 'analyzed',
                'signal': 'bullish' if symbol == 'TQQQ' else 'bearish',
                'current_price': 104.74,
                'ema_10': 105.72,
                'ema_20': 106.93
            }
        
        mock_analyze.side_effect = analyze_side_effect
        
        symbols = ['TQQQ', 'SPY']
        results = self.signal.analyze_multiple(symbols)
        
        assert len(results) == 2
        assert results['TQQQ']['signal'] == 'bullish'
        assert results['SPY']['signal'] == 'bearish'
        assert mock_analyze.call_count == 2
    
    @patch('signals.twelve_data_ema.TwelveDataEMASignal.analyze')
    def test_analyze_multiple_with_error(self, mock_analyze):
        """Test multiple analysis with one symbol erroring."""
        def analyze_side_effect(symbol):
            if symbol == 'INVALID':
                raise Exception("Invalid symbol")
            return {
                'status': 'analyzed',
                'signal': 'bullish',
                'current_price': 104.74
            }
        
        mock_analyze.side_effect = analyze_side_effect
        
        symbols = ['TQQQ', 'INVALID']
        results = self.signal.analyze_multiple(symbols)
        
        assert len(results) == 2
        assert results['TQQQ']['status'] == 'analyzed'
        assert results['INVALID']['status'] == 'error'
        assert 'Invalid symbol' in results['INVALID']['message']