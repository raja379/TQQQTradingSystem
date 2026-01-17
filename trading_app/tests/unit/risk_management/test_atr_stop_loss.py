"""
Unit tests for ATRStopLoss strategy.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from risk_management.atr_stop_loss import ATRStopLoss


class TestATRStopLoss:
    """Test cases for ATRStopLoss strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock data connector
        self.mock_connector = Mock()
        self.mock_connector.get_stock_data = MagicMock()

    def _create_test_data(self, periods: int = 20) -> pd.DataFrame:
        """
        Create test OHLC data for ATR calculation.

        Creates realistic volatile price action similar to TQQQ.
        """
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='h')

        # Simulate volatile price action
        base_price = 100.0
        data = []

        for i, date in enumerate(dates):
            # Create intraday volatility
            open_price = base_price + (i * 0.5) + (-1 if i % 3 == 0 else 1) * 2
            high = open_price + 3.0
            low = open_price - 2.5
            close = open_price + (1 if i % 2 == 0 else -1) * 1.5

            data.append({
                'Date': date,
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': close,
                'Volume': 1000000
            })

        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)
        return df

    def test_initialization_basic(self):
        """Test basic initialization."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        assert strategy.atr_multiplier == 2.0
        assert strategy.atr_period == 14
        assert strategy.reward_risk_ratio is None
        assert strategy.cache_duration_minutes == 30
        assert strategy.fallback_percentage == 0.05

    def test_initialization_with_reward_risk(self):
        """Test initialization with reward:risk ratio."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            reward_risk_ratio=3.0
        )

        assert strategy.reward_risk_ratio == 3.0

    def test_initialization_with_custom_cache(self):
        """Test initialization with custom cache duration."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            cache_duration_minutes=60
        )

        assert strategy.cache_duration_minutes == 60

    def test_calculate_true_range(self):
        """Test True Range calculation."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        # Create simple test data
        df = pd.DataFrame({
            'High': [105, 108, 107],
            'Low': [100, 103, 102],
            'Close': [103, 106, 104]
        })

        tr = strategy._calculate_true_range(df)

        # First TR uses high-low since there's no previous close
        # max(105-100=5, NaN, NaN) = 5
        assert tr.iloc[0] == 5.0

        # Second TR: max(108-103=5, |108-103|=5, |103-103|=0) = 5
        assert tr.iloc[1] == 5.0

        # Third TR: max(107-102=5, |107-106|=1, |102-106|=4) = 5
        assert tr.iloc[2] == 5.0

    def test_calculate_atr(self):
        """Test ATR calculation with known values."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=5,  # Use smaller period for easier testing
            data_connector=self.mock_connector
        )

        df = self._create_test_data(periods=10)
        atr = strategy._calculate_atr(df)

        assert atr is not None
        assert isinstance(atr, float)
        assert atr > 0

    def test_calculate_atr_insufficient_data(self):
        """Test ATR calculation with insufficient data."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        # Only 5 bars, need at least 15 (period + 1)
        df = self._create_test_data(periods=5)
        atr = strategy._calculate_atr(df)

        assert atr is None

    def test_cache_and_retrieve_atr(self):
        """Test ATR caching mechanism."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            cache_duration_minutes=30
        )

        # Cache a value
        strategy._cache_atr("TQQQ", 3.5)

        # Retrieve it immediately
        cached = strategy._get_cached_atr("TQQQ")
        assert cached == 3.5

    def test_cache_expiration(self):
        """Test ATR cache expiration."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            cache_duration_minutes=30
        )

        # Manually set an expired cache entry
        old_timestamp = datetime.now() - timedelta(minutes=35)
        strategy._atr_cache["TQQQ"] = (3.5, old_timestamp)

        # Should return None (expired)
        cached = strategy._get_cached_atr("TQQQ")
        assert cached is None

    def test_calculate_stop_price_with_atr(self):
        """Test stop price calculation using ATR."""
        self.mock_connector.get_stock_data.return_value = self._create_test_data(periods=20)

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        stop_price = strategy.calculate_stop_price(100.0, "TQQQ")

        # Should be calculated as: entry - (2.0 * ATR)
        # ATR will be around 5.0-6.0 based on our test data
        # So stop should be around 90-88
        assert stop_price < 100.0
        assert stop_price > 80.0  # Reasonable range

        # Verify data was fetched
        self.mock_connector.get_stock_data.assert_called_once()

    def test_calculate_stop_price_uses_cache(self):
        """Test that subsequent calls use cached ATR."""
        self.mock_connector.get_stock_data.return_value = self._create_test_data(periods=20)

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        # First call - should fetch data
        stop1 = strategy.calculate_stop_price(100.0, "TQQQ")
        assert self.mock_connector.get_stock_data.call_count == 1

        # Second call - should use cache
        stop2 = strategy.calculate_stop_price(100.0, "TQQQ")
        assert self.mock_connector.get_stock_data.call_count == 1  # Not called again

        # Stops should be the same
        assert stop1 == stop2

    def test_calculate_stop_price_fallback(self):
        """Test fallback to percentage when ATR fails."""
        # Mock connector returns None (simulating API failure)
        self.mock_connector.get_stock_data.return_value = None

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            fallback_percentage=0.05
        )

        stop_price = strategy.calculate_stop_price(100.0, "TQQQ")

        # Should use 5% fallback
        assert stop_price == 95.0

    def test_calculate_take_profit_not_set(self):
        """Test take profit when not configured."""
        self.mock_connector.get_stock_data.return_value = self._create_test_data(periods=20)

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        take_profit = strategy.calculate_take_profit_price(100.0, "TQQQ")
        assert take_profit is None

    def test_calculate_take_profit_with_reward_risk(self):
        """Test take profit calculation with reward:risk ratio."""
        self.mock_connector.get_stock_data.return_value = self._create_test_data(periods=20)

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            reward_risk_ratio=3.0
        )

        entry = 100.0
        stop = strategy.calculate_stop_price(entry, "TQQQ")
        target = strategy.calculate_take_profit_price(entry, "TQQQ")

        # Calculate expected values
        risk = entry - stop
        expected_reward = risk * 3.0
        expected_target = entry + expected_reward

        assert target is not None
        assert abs(target - expected_target) < 0.01  # Allow small rounding difference

    def test_get_strategy_name_basic(self):
        """Test strategy name without reward:risk."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        name = strategy.get_strategy_name()
        assert "ATR-Based" in name
        assert "2.0x" in name
        assert "14-period" in name

    def test_get_strategy_name_with_reward_risk(self):
        """Test strategy name with reward:risk ratio."""
        strategy = ATRStopLoss(
            atr_multiplier=1.5,
            atr_period=10,
            data_connector=self.mock_connector,
            reward_risk_ratio=3.0
        )

        name = strategy.get_strategy_name()
        assert "ATR-Based" in name
        assert "1.5x" in name
        assert "10-period" in name
        assert "R:R 3.0:1" in name

    def test_validation_atr_multiplier_too_small(self):
        """Test validation fails for ATR multiplier too small."""
        with pytest.raises(ValueError, match="must be between 0.5 and 5.0"):
            ATRStopLoss(
                atr_multiplier=0.3,
                atr_period=14,
                data_connector=self.mock_connector
            )

    def test_validation_atr_multiplier_too_large(self):
        """Test validation fails for ATR multiplier too large."""
        with pytest.raises(ValueError, match="must be between 0.5 and 5.0"):
            ATRStopLoss(
                atr_multiplier=6.0,
                atr_period=14,
                data_connector=self.mock_connector
            )

    def test_validation_atr_period_too_small(self):
        """Test validation fails for ATR period too small."""
        with pytest.raises(ValueError, match="must be between 5 and 50"):
            ATRStopLoss(
                atr_multiplier=2.0,
                atr_period=3,
                data_connector=self.mock_connector
            )

    def test_validation_atr_period_too_large(self):
        """Test validation fails for ATR period too large."""
        with pytest.raises(ValueError, match="must be between 5 and 50"):
            ATRStopLoss(
                atr_multiplier=2.0,
                atr_period=60,
                data_connector=self.mock_connector
            )

    def test_validation_reward_risk_negative(self):
        """Test validation fails for negative reward:risk."""
        with pytest.raises(ValueError, match="must be positive"):
            ATRStopLoss(
                atr_multiplier=2.0,
                atr_period=14,
                data_connector=self.mock_connector,
                reward_risk_ratio=-1.0
            )

    def test_validation_no_data_connector(self):
        """Test validation fails without data connector."""
        with pytest.raises(ValueError, match="cannot be None"):
            ATRStopLoss(
                atr_multiplier=2.0,
                atr_period=14,
                data_connector=None
            )

    def test_different_multipliers(self):
        """Test different ATR multipliers."""
        self.mock_connector.get_stock_data.return_value = self._create_test_data(periods=20)

        multipliers = [1.5, 2.0, 3.0]
        stops = []

        for mult in multipliers:
            strategy = ATRStopLoss(
                atr_multiplier=mult,
                atr_period=14,
                data_connector=self.mock_connector
            )
            # Clear cache between tests
            strategy._atr_cache.clear()
            self.mock_connector.get_stock_data.return_value = self._create_test_data(periods=20)

            stop = strategy.calculate_stop_price(100.0, "TQQQ")
            stops.append(stop)

        # Higher multiplier should give tighter stop (closer to entry)
        assert stops[0] > stops[1] > stops[2]  # 1.5x > 2.0x > 3.0x

    def test_realistic_tqqq_scenario(self):
        """Test with realistic TQQQ volatile price action."""
        # Create realistic volatile TQQQ data
        df = pd.DataFrame({
            'High': [72, 75, 73, 76, 74, 78, 76, 80, 77, 81, 79, 83, 80, 84, 82],
            'Low': [68, 71, 69, 72, 70, 74, 72, 76, 73, 77, 75, 79, 76, 80, 78],
            'Close': [70, 73, 71, 74, 72, 76, 74, 78, 75, 79, 77, 81, 78, 82, 80]
        })
        df.index = pd.date_range(end=datetime.now(), periods=len(df), freq='h')

        self.mock_connector.get_stock_data.return_value = df

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            reward_risk_ratio=3.0
        )

        entry = 80.0
        stop = strategy.calculate_stop_price(entry, "TQQQ")
        target = strategy.calculate_take_profit_price(entry, "TQQQ")

        # Stop should be reasonable for TQQQ
        assert 70.0 <= stop < 78.0  # Allow equal to 70.0
        assert target > entry
        assert target > 80.0

    def test_calculate_stop_price_invalid_entry(self):
        """Test stop calculation fails for invalid entry price."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector
        )

        with pytest.raises(ValueError, match="must be positive"):
            strategy.calculate_stop_price(0.0, "TQQQ")

        with pytest.raises(ValueError, match="must be positive"):
            strategy.calculate_stop_price(-100.0, "TQQQ")

    def test_str_representation(self):
        """Test string representation of strategy."""
        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=self.mock_connector,
            reward_risk_ratio=3.0
        )

        str_repr = str(strategy)
        assert "ATR-Based" in str_repr
        assert "2.0x" in str_repr
        assert "14-period" in str_repr
