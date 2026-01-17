"""
Unit tests for PercentageStopLoss strategy.
"""

import pytest
from risk_management.percentage_stop_loss import PercentageStopLoss


class TestPercentageStopLoss:
    """Test cases for PercentageStopLoss strategy."""

    def test_initialization_basic(self):
        """Test basic initialization with stop loss only."""
        strategy = PercentageStopLoss(stop_loss_pct=0.05)

        assert strategy.stop_loss_pct == 0.05
        assert strategy.take_profit_pct is None
        assert strategy.min_stop_distance is None
        assert strategy.max_stop_distance is None

    def test_initialization_with_take_profit(self):
        """Test initialization with take profit."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        assert strategy.stop_loss_pct == 0.05
        assert strategy.take_profit_pct == 0.15

    def test_initialization_with_constraints(self):
        """Test initialization with min/max constraints."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            min_stop_distance=1.0,
            max_stop_distance=10.0
        )

        assert strategy.min_stop_distance == 1.0
        assert strategy.max_stop_distance == 10.0

    def test_calculate_stop_price_5_percent(self):
        """Test stop price calculation with 5% stop."""
        strategy = PercentageStopLoss(stop_loss_pct=0.05)

        # TQQQ at $100
        stop_price = strategy.calculate_stop_price(100.0, "TQQQ")
        assert stop_price == 95.0

        # TQQQ at $70
        stop_price = strategy.calculate_stop_price(70.0, "TQQQ")
        assert stop_price == 66.5

        # TQQQ at $50
        stop_price = strategy.calculate_stop_price(50.0, "TQQQ")
        assert stop_price == 47.5

    def test_calculate_stop_price_3_percent(self):
        """Test stop price calculation with 3% stop."""
        strategy = PercentageStopLoss(stop_loss_pct=0.03)

        stop_price = strategy.calculate_stop_price(100.0, "TQQQ")
        assert stop_price == 97.0

    def test_calculate_stop_price_10_percent(self):
        """Test stop price calculation with 10% stop."""
        strategy = PercentageStopLoss(stop_loss_pct=0.10)

        stop_price = strategy.calculate_stop_price(100.0, "TQQQ")
        assert stop_price == 90.0

    def test_calculate_take_profit_not_set(self):
        """Test take profit when not configured."""
        strategy = PercentageStopLoss(stop_loss_pct=0.05)

        take_profit = strategy.calculate_take_profit_price(100.0, "TQQQ")
        assert take_profit is None

    def test_calculate_take_profit_15_percent(self):
        """Test take profit calculation with 15% target."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        # 3:1 reward:risk ratio
        take_profit = strategy.calculate_take_profit_price(100.0, "TQQQ")
        assert take_profit == 115.0

    def test_min_stop_distance_enforcement(self):
        """Test minimum stop distance enforcement."""
        # With 1% stop on $50 stock, distance would be $0.50
        # But min is $1.00, so should use $1.00
        strategy = PercentageStopLoss(
            stop_loss_pct=0.01,
            min_stop_distance=1.0
        )

        stop_price = strategy.calculate_stop_price(50.0, "TQQQ")
        # Should be $50 - $1 = $49 (not $50 - $0.50 = $49.50)
        assert stop_price == 49.0

    def test_max_stop_distance_enforcement(self):
        """Test maximum stop distance enforcement."""
        # With 10% stop on $100 stock, distance would be $10
        # But max is $5.00, so should use $5.00
        strategy = PercentageStopLoss(
            stop_loss_pct=0.10,
            max_stop_distance=5.0
        )

        stop_price = strategy.calculate_stop_price(100.0, "TQQQ")
        # Should be $100 - $5 = $95 (not $100 - $10 = $90)
        assert stop_price == 95.0

    def test_get_strategy_name_basic(self):
        """Test strategy name without take profit."""
        strategy = PercentageStopLoss(stop_loss_pct=0.05)

        name = strategy.get_strategy_name()
        assert "Percentage-Based" in name
        assert "5.0%" in name

    def test_get_strategy_name_with_reward_risk(self):
        """Test strategy name with reward:risk ratio."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        name = strategy.get_strategy_name()
        assert "Percentage-Based" in name
        assert "5.0%" in name
        assert "R:R 3.0:1" in name

    def test_validation_stop_too_small(self):
        """Test validation fails for stop percentage too small."""
        with pytest.raises(ValueError, match="must be between 0.001 and 0.5"):
            PercentageStopLoss(stop_loss_pct=0.0005)

    def test_validation_stop_too_large(self):
        """Test validation fails for stop percentage too large."""
        with pytest.raises(ValueError, match="must be between 0.001 and 0.5"):
            PercentageStopLoss(stop_loss_pct=0.6)

    def test_validation_take_profit_negative(self):
        """Test validation fails for negative take profit."""
        with pytest.raises(ValueError, match="must be positive"):
            PercentageStopLoss(
                stop_loss_pct=0.05,
                take_profit_pct=-0.1
            )

    def test_validation_min_exceeds_max(self):
        """Test validation fails when min exceeds max."""
        with pytest.raises(ValueError, match="cannot exceed max_stop_distance"):
            PercentageStopLoss(
                stop_loss_pct=0.05,
                min_stop_distance=10.0,
                max_stop_distance=5.0
            )

    def test_validation_negative_min_distance(self):
        """Test validation fails for negative min distance."""
        with pytest.raises(ValueError, match="must be non-negative"):
            PercentageStopLoss(
                stop_loss_pct=0.05,
                min_stop_distance=-1.0
            )

    def test_calculate_stop_price_invalid_entry(self):
        """Test stop calculation fails for invalid entry price."""
        strategy = PercentageStopLoss(stop_loss_pct=0.05)

        with pytest.raises(ValueError, match="must be positive"):
            strategy.calculate_stop_price(0.0, "TQQQ")

        with pytest.raises(ValueError, match="must be positive"):
            strategy.calculate_stop_price(-100.0, "TQQQ")

    def test_calculate_take_profit_invalid_entry(self):
        """Test take profit calculation fails for invalid entry price."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        with pytest.raises(ValueError, match="must be positive"):
            strategy.calculate_take_profit_price(0.0, "TQQQ")

    def test_realistic_tqqq_scenarios(self):
        """Test realistic TQQQ trading scenarios."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        # TQQQ at different price points
        scenarios = [
            (50.0, 47.5, 57.5),   # Lower price
            (70.0, 66.5, 80.5),   # Mid price
            (100.0, 95.0, 115.0), # Round number
            (104.74, 99.50, 120.45) # Realistic current price
        ]

        for entry, expected_stop, expected_target in scenarios:
            stop = strategy.calculate_stop_price(entry, "TQQQ")
            target = strategy.calculate_take_profit_price(entry, "TQQQ")

            assert stop == expected_stop, f"Stop mismatch for entry ${entry}"
            assert target == expected_target, f"Target mismatch for entry ${entry}"

    def test_edge_case_very_small_percentage(self):
        """Test edge case with very small percentage (0.1%)."""
        strategy = PercentageStopLoss(stop_loss_pct=0.001)

        stop = strategy.calculate_stop_price(100.0, "TQQQ")
        assert stop == 99.9

    def test_edge_case_large_percentage(self):
        """Test edge case with large percentage (50%)."""
        strategy = PercentageStopLoss(stop_loss_pct=0.5)

        stop = strategy.calculate_stop_price(100.0, "TQQQ")
        assert stop == 50.0

    def test_rounding_precision(self):
        """Test that prices are rounded to 2 decimal places."""
        strategy = PercentageStopLoss(stop_loss_pct=0.0333)  # 3.33%

        # Should round to 2 decimals
        stop = strategy.calculate_stop_price(100.0, "TQQQ")
        assert isinstance(stop, float)
        # 100 - 3.33 = 96.67
        assert stop == 96.67

    def test_str_representation(self):
        """Test string representation of strategy."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        str_repr = str(strategy)
        assert "Percentage-Based" in str_repr
        assert "5.0%" in str_repr
