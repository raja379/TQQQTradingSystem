"""
Integration tests for stop loss strategies with AlpacaTrader.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd

from trading.alpaca_trader import AlpacaTrader, AlpacaOrder
from risk_management.percentage_stop_loss import PercentageStopLoss
from risk_management.atr_stop_loss import ATRStopLoss


class TestStopLossIntegration:
    """Integration tests for stop loss strategies with AlpacaTrader."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock credentials
        self.credentials_patch = patch('trading.alpaca_trader.AlpacaTrader._get_alpaca_credentials')
        mock_creds = self.credentials_patch.start()
        mock_creds.return_value = ('test_key', 'test_secret')

    def teardown_method(self):
        """Clean up patches."""
        self.credentials_patch.stop()

    def test_alpaca_trader_with_percentage_stop_loss(self):
        """Test AlpacaTrader with PercentageStopLoss strategy."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        assert trader.stop_loss_strategy is not None
        assert trader.stop_loss_strategy.get_strategy_name() == "Percentage-Based (5.0%) [R:R 3.0:1]"

    def test_alpaca_trader_with_atr_stop_loss(self):
        """Test AlpacaTrader with ATRStopLoss strategy."""
        mock_connector = Mock()

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=mock_connector,
            reward_risk_ratio=3.0
        )

        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        assert trader.stop_loss_strategy is not None
        assert "ATR-Based" in trader.stop_loss_strategy.get_strategy_name()

    def test_alpaca_trader_without_stop_loss(self):
        """Test AlpacaTrader without stop loss strategy (backward compatible)."""
        trader = AlpacaTrader(paper_trading=True)

        assert trader.stop_loss_strategy is None

    def test_set_stop_loss_strategy(self):
        """Test changing stop loss strategy at runtime."""
        trader = AlpacaTrader(paper_trading=True)
        assert trader.stop_loss_strategy is None

        # Set percentage strategy
        percentage_strategy = PercentageStopLoss(stop_loss_pct=0.05)
        trader.set_stop_loss_strategy(percentage_strategy)
        assert trader.stop_loss_strategy is not None
        assert "Percentage-Based" in trader.stop_loss_strategy.get_strategy_name()

        # Change to ATR strategy
        mock_connector = Mock()
        atr_strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=mock_connector
        )
        trader.set_stop_loss_strategy(atr_strategy)
        assert "ATR-Based" in trader.stop_loss_strategy.get_strategy_name()

        # Disable strategy
        trader.set_stop_loss_strategy(None)
        assert trader.stop_loss_strategy is None

    @patch('requests.post')
    def test_place_buy_order_with_percentage_stop_loss(self, mock_post):
        """Test placing buy order with percentage stop loss."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        # Mock successful order response
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'order-123', 'status': 'new'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        order = trader.place_buy_order(
            symbol="TQQQ",
            price=100.0,
            reason="Test order",
            quantity=10,
            use_stop_loss=True
        )

        assert order is not None
        assert order.symbol == "TQQQ"
        assert order.quantity == 10
        assert order.stop_price == 95.0  # 5% stop
        assert order.take_profit_price == 115.0  # 15% target

        # Verify bracket order was sent to API
        call_args = mock_post.call_args
        order_data = call_args[1]['json']

        assert order_data['order_class'] == 'bracket'
        assert order_data['stop_loss']['stop_price'] == '95.0'
        assert order_data['take_profit']['limit_price'] == '115.0'

    @patch('requests.post')
    def test_place_buy_order_without_stop_loss(self, mock_post):
        """Test placing buy order without stop loss."""
        trader = AlpacaTrader(paper_trading=True)  # No strategy

        # Mock successful order response
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'order-123', 'status': 'new'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        order = trader.place_buy_order(
            symbol="TQQQ",
            price=100.0,
            reason="Test order",
            quantity=10,
            use_stop_loss=True  # True, but no strategy set
        )

        assert order is not None
        assert order.stop_price is None
        assert order.take_profit_price is None

        # Verify regular order (not bracket) was sent
        call_args = mock_post.call_args
        order_data = call_args[1]['json']

        assert 'order_class' not in order_data
        assert 'stop_loss' not in order_data
        assert 'take_profit' not in order_data

    @patch('requests.post')
    def test_place_buy_order_disable_stop_loss(self, mock_post):
        """Test placing buy order with strategy set but use_stop_loss=False."""
        strategy = PercentageStopLoss(stop_loss_pct=0.05)
        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        # Mock successful order response
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'order-123', 'status': 'new'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        order = trader.place_buy_order(
            symbol="TQQQ",
            price=100.0,
            reason="Test order",
            quantity=10,
            use_stop_loss=False  # Explicitly disable
        )

        assert order is not None
        assert order.stop_price is None
        assert order.take_profit_price is None

    @patch('requests.post')
    def test_place_buy_order_with_atr_stop_loss(self, mock_post):
        """Test placing buy order with ATR stop loss."""
        # Mock data connector
        mock_connector = Mock()
        test_data = pd.DataFrame({
            'High': [105, 108, 110, 107, 112] * 4,
            'Low': [100, 103, 105, 102, 107] * 4,
            'Close': [103, 106, 108, 105, 110] * 4
        })
        test_data.index = pd.date_range(end=datetime.now(), periods=20, freq='h')
        mock_connector.get_stock_data.return_value = test_data

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=mock_connector,
            reward_risk_ratio=3.0
        )

        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        # Mock successful order response
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'order-456', 'status': 'new'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        order = trader.place_buy_order(
            symbol="TQQQ",
            price=100.0,
            reason="Test order with ATR",
            quantity=10,
            use_stop_loss=True
        )

        assert order is not None
        assert order.symbol == "TQQQ"
        assert order.stop_price is not None
        assert order.stop_price < 100.0  # Stop should be below entry
        assert order.take_profit_price is not None
        assert order.take_profit_price > 100.0  # Target should be above entry

        # Verify bracket order was sent
        call_args = mock_post.call_args
        order_data = call_args[1]['json']
        assert order_data['order_class'] == 'bracket'

    @patch('requests.get')
    @patch('requests.post')
    def test_buy_tqqq_with_all_funds_and_stop_loss(self, mock_post, mock_get):
        """Test buying TQQQ with all funds using stop loss."""
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        # Mock account info
        mock_account_response = Mock()
        mock_account_response.json.return_value = {
            'status': 'ACTIVE',
            'buying_power': '10000.0'
        }
        mock_account_response.raise_for_status = Mock()
        mock_get.return_value = mock_account_response

        # Mock order response
        mock_order_response = Mock()
        mock_order_response.json.return_value = {'id': 'order-789', 'status': 'new'}
        mock_order_response.raise_for_status = Mock()
        mock_post.return_value = mock_order_response

        order = trader.buy_tqqq_with_all_funds(tqqq_price=100.0)

        assert order is not None
        assert order.symbol == "TQQQ"
        assert order.quantity == 95  # ($10,000 * 0.95) / $100
        assert order.stop_price == 95.0
        assert order.take_profit_price == 115.0

    @patch('trading.alpaca_trader.AlpacaTrader.get_account')
    @patch('trading.alpaca_trader.AlpacaTrader.sell_all_positions_except')
    @patch('trading.alpaca_trader.AlpacaTrader.buy_tqqq_with_all_funds')
    def test_process_all_stocks_includes_strategy_info(
        self, mock_buy_tqqq, mock_sell_all, mock_get_account
    ):
        """Test that process_all_stocks includes stop loss strategy info."""
        strategy = PercentageStopLoss(stop_loss_pct=0.05)
        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        mock_get_account.return_value = {'status': 'ACTIVE', 'buying_power': '10000.0'}
        mock_sell_all.return_value = []
        mock_buy_tqqq.return_value = AlpacaOrder(
            symbol='TQQQ',
            action='BUY',
            quantity=100,
            price=100.0,
            amount=10000.0,
            order_id='order-1',
            status='new',
            timestamp=datetime.now().isoformat(),
            reason='Test',
            stop_price=95.0,
            take_profit_price=None
        )

        market_signals = {
            'TQQQ': {
                'status': 'analyzed',
                'signal': 'bullish',
                'current_price': 100.0,
                'ema_10': 98.0,
                'ema_20': 96.0
            }
        }

        result = trader.process_all_stocks(market_signals)

        assert result['stop_loss_strategy'] == "Percentage-Based (5.0%)"
        assert len(result['orders']) == 1
        assert result['orders'][0]['stop_price'] == 95.0

    def test_backward_compatibility_no_strategy(self):
        """Test that system works exactly as before when no strategy is provided."""
        trader = AlpacaTrader(paper_trading=True)

        assert trader.stop_loss_strategy is None
        # System should work exactly as before (no bracket orders)

    @patch('requests.post')
    def test_stop_loss_calculation_failure_fallback(self, mock_post):
        """Test that order still works if stop loss calculation fails."""
        # Create a broken strategy (will fail on calculation)
        mock_connector = Mock()
        mock_connector.get_stock_data.side_effect = Exception("API failure")

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=mock_connector,
            fallback_percentage=0.05
        )

        trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=strategy)

        # Mock successful order response
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'order-999', 'status': 'new'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Should still place order using fallback
        order = trader.place_buy_order(
            symbol="TQQQ",
            price=100.0,
            reason="Test with failure",
            quantity=10,
            use_stop_loss=True
        )

        assert order is not None
        # Should use fallback percentage (5%)
        assert order.stop_price == 95.0
