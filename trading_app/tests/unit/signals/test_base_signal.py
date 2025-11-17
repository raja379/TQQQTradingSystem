"""
Unit tests for BaseSignal class.
"""

import pytest
from signals.base_signal import BaseSignal


class TestSignal(BaseSignal):
    """Test implementation of BaseSignal for testing."""
    
    def analyze(self, symbol: str):
        return {"symbol": symbol, "signal": "test"}
    
    def analyze_multiple(self, symbols):
        return {symbol: self.analyze(symbol) for symbol in symbols}


class TestBaseSignal:
    """Test cases for BaseSignal class."""
    
    def test_base_signal_initialization(self):
        """Test BaseSignal initialization."""
        signal = TestSignal("test_signal")
        assert signal.name == "test_signal"
    
    def test_get_signal_type_bullish(self):
        """Test bullish signal detection."""
        signal = TestSignal("test")
        result = signal.get_signal_type(price=110, ema_10=105, ema_20=100)
        assert result == "bullish"
    
    def test_get_signal_type_bearish(self):
        """Test bearish signal detection."""
        signal = TestSignal("test")
        result = signal.get_signal_type(price=95, ema_10=100, ema_20=105)
        assert result == "bearish"
    
    def test_get_signal_type_neutral_price_between_emas(self):
        """Test neutral signal when price is between EMAs."""
        signal = TestSignal("test")
        result = signal.get_signal_type(price=102.5, ema_10=105, ema_20=100)
        assert result == "neutral"
    
    def test_get_signal_type_neutral_emas_crossed(self):
        """Test neutral signal when EMAs are crossed."""
        signal = TestSignal("test")
        result = signal.get_signal_type(price=110, ema_10=100, ema_20=105)
        assert result == "neutral"
    
    def test_get_signal_type_edge_case_equal_values(self):
        """Test edge case with equal values."""
        signal = TestSignal("test")
        result = signal.get_signal_type(price=100, ema_10=100, ema_20=100)
        assert result == "neutral"
    
    @pytest.mark.parametrize("price,ema_10,ema_20,expected", [
        (110, 105, 100, "bullish"),   # Clear bullish
        (95, 100, 105, "bearish"),    # Clear bearish  
        (102, 105, 100, "neutral"),   # Price between EMAs
        (110, 100, 105, "neutral"),   # EMAs crossed
        (100, 100, 100, "neutral"),   # All equal
        (105, 105, 100, "neutral"),   # Price equals fast EMA
        (100, 105, 100, "neutral"),   # Slow EMA equals price
    ])
    def test_get_signal_type_parametrized(self, price, ema_10, ema_20, expected):
        """Parametrized test for various signal conditions."""
        signal = TestSignal("test")
        result = signal.get_signal_type(price, ema_10, ema_20)
        assert result == expected