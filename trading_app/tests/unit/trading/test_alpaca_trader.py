"""
Unit tests for AlpacaTrader class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from trading.alpaca_trader import AlpacaTrader, AlpacaOrder


class TestAlpacaTrader:
    """Test cases for AlpacaTrader class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('trading.alpaca_trader.AlpacaTrader._get_alpaca_credentials') as mock_creds:
            mock_creds.return_value = ('test_key', 'test_secret')
            self.trader = AlpacaTrader(paper_trading=True)
    
    def test_initialization_paper_trading(self):
        """Test trader initialization in paper trading mode."""
        assert self.trader.paper_trading is True
        assert 'paper-api.alpaca.markets' in self.trader.base_url
        assert self.trader.api_key == 'test_key'
        assert self.trader.secret_key == 'test_secret'
    
    def test_initialization_live_trading(self):
        """Test trader initialization in live trading mode."""
        with patch('trading.alpaca_trader.AlpacaTrader._get_alpaca_credentials') as mock_creds:
            mock_creds.return_value = ('test_key', 'test_secret')
            trader = AlpacaTrader(paper_trading=False)
            assert trader.paper_trading is False
            assert 'api.alpaca.markets' in trader.base_url
    
    @patch('boto3.client')
    @patch('os.environ.get')
    def test_get_alpaca_credentials_success(self, mock_env, mock_boto):
        """Test successful credential retrieval."""
        mock_env.return_value = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test'
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.get_secret_value.return_value = {
            'SecretString': '{"alpaca_key_id": "key123", "alpaca_secret_key": "secret456"}'
        }
        
        trader = AlpacaTrader()
        api_key, secret_key = trader._get_alpaca_credentials()
        
        assert api_key == 'key123'
        assert secret_key == 'secret456'
    
    @patch('requests.get')
    def test_get_account_success(self, mock_requests):
        """Test successful account retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'ACTIVE',
            'buying_power': '197994.15',
            'cash': '197994.15'
        }
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response
        
        result = self.trader.get_account()
        
        assert result['status'] == 'ACTIVE'
        assert result['buying_power'] == '197994.15'
        mock_requests.assert_called_once()
    
    @patch('requests.get')
    def test_get_position_success(self, mock_requests):
        """Test successful position retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'symbol': 'TQQQ',
            'qty': '100',
            'avg_entry_price': '104.50'
        }
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response
        
        result = self.trader.get_position('TQQQ')
        
        assert result['symbol'] == 'TQQQ'
        assert result['qty'] == '100'
    
    @patch('requests.get')
    def test_get_position_not_found(self, mock_requests):
        """Test position retrieval when position doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.return_value = mock_response
        
        result = self.trader.get_position('TQQQ')
        
        assert result is None
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    def test_should_buy_bullish_no_position(self, mock_get_position):
        """Test buy decision when bullish and no position."""
        mock_get_position.return_value = None
        
        should_buy, reason = self.trader.should_buy('TQQQ', 110, 108, 106)
        
        assert should_buy is True
        assert 'BUY signal' in reason
        assert 'BUY signal' in reason
        assert '$110.00' in reason and '$108.00' in reason and '$106.00' in reason
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    def test_should_buy_bearish_signal(self, mock_get_position):
        """Test buy decision when bearish signal."""
        mock_get_position.return_value = None
        
        should_buy, reason = self.trader.should_buy('TQQQ', 104, 106, 108)
        
        assert should_buy is False
        assert 'No buy signal' in reason
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    def test_should_buy_already_have_position(self, mock_get_position):
        """Test buy decision when already have position."""
        mock_get_position.return_value = {'qty': '100'}
        
        should_buy, reason = self.trader.should_buy('TQQQ', 110, 108, 106)
        
        assert should_buy is False
        assert 'Already have position' in reason
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    def test_should_sell_bearish_with_position(self, mock_get_position):
        """Test sell decision when bearish and have position."""
        mock_get_position.return_value = {'qty': '100'}
        
        should_sell, reason = self.trader.should_sell('TQQQ', 104, 106, 108)
        
        assert should_sell is True
        assert 'SELL signal' in reason
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    def test_should_sell_bullish_with_position(self, mock_get_position):
        """Test sell decision when bullish and have position."""
        mock_get_position.return_value = {'qty': '100'}
        
        should_sell, reason = self.trader.should_sell('TQQQ', 110, 108, 106)
        
        assert should_sell is False
        assert 'Hold position' in reason
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    def test_should_sell_no_position(self, mock_get_position):
        """Test sell decision when no position."""
        mock_get_position.return_value = None
        
        should_sell, reason = self.trader.should_sell('TQQQ', 104, 106, 108)
        
        assert should_sell is False
        assert 'No position' in reason
    
    @patch('requests.post')
    def test_place_buy_order_success(self, mock_requests):
        """Test successful buy order placement."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'order-123',
            'status': 'new'
        }
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response
        
        result = self.trader.place_buy_order('TQQQ', 104.74, 'Test buy', quantity=100)
        
        assert isinstance(result, AlpacaOrder)
        assert result.symbol == 'TQQQ'
        assert result.action == 'BUY'
        assert result.quantity == 100
        assert result.order_id == 'order-123'
        mock_requests.assert_called_once()
    
    def test_place_buy_order_invalid_quantity(self):
        """Test buy order with invalid quantity."""
        result = self.trader.place_buy_order('TQQQ', 104.74, 'Test buy', quantity=0)
        
        assert result is None
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    @patch('requests.post')
    def test_place_sell_order_success(self, mock_requests, mock_get_position):
        """Test successful sell order placement."""
        mock_get_position.return_value = {'qty': '100'}
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'order-456',
            'status': 'new'
        }
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response
        
        result = self.trader.place_sell_order('TQQQ', 104.74, 'Test sell')
        
        assert isinstance(result, AlpacaOrder)
        assert result.symbol == 'TQQQ'
        assert result.action == 'SELL'
        assert result.quantity == 100
        assert result.order_id == 'order-456'
    
    @patch('requests.get')
    def test_get_all_positions(self, mock_requests):
        """Test getting all positions."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {'symbol': 'TQQQ', 'qty': '100'},
            {'symbol': 'SPY', 'qty': '50'}
        ]
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response
        
        result = self.trader.get_all_positions()
        
        assert len(result) == 2
        assert result[0]['symbol'] == 'TQQQ'
        assert result[1]['symbol'] == 'SPY'
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_all_positions')
    @patch('requests.post')
    def test_sell_all_positions_except(self, mock_requests, mock_get_positions):
        """Test selling all positions except specified symbol."""
        mock_get_positions.return_value = [
            {'symbol': 'SPY', 'qty': '50', 'market_value': '21275'},
            {'symbol': 'TQQQ', 'qty': '100', 'market_value': '10474'},
            {'symbol': 'QQQ', 'qty': '25', 'market_value': '12500'}
        ]
        
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'order-123', 'status': 'new'}
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response
        
        result = self.trader.sell_all_positions_except('TQQQ')
        
        assert len(result) == 2  # Should sell SPY and QQQ, but not TQQQ
        assert all(order.action == 'SELL' for order in result)
        assert mock_requests.call_count == 2
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_account')
    @patch('requests.post')
    def test_buy_tqqq_with_all_funds(self, mock_requests, mock_get_account):
        """Test buying TQQQ with all available funds."""
        mock_get_account.return_value = {
            'buying_power': '197994.15',
            'status': 'ACTIVE'
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'order-789', 'status': 'new'}
        mock_response.raise_for_status = Mock()
        mock_requests.return_value = mock_response
        
        result = self.trader.buy_tqqq_with_all_funds(104.74)
        
        assert isinstance(result, AlpacaOrder)
        assert result.symbol == 'TQQQ'
        assert result.action == 'BUY'
        # Should buy about 1789 shares (197994.15 * 0.95 / 104.74)
        expected_quantity = int(197994.15 * 0.95 / 104.74)
        assert result.quantity == expected_quantity
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_account')
    @patch('trading.alpaca_trader.AlpacaTrader.sell_all_positions_except')
    @patch('trading.alpaca_trader.AlpacaTrader.buy_tqqq_with_all_funds')
    def test_process_all_stocks_bullish_signal(self, mock_buy_tqqq, mock_sell_all, mock_get_account):
        """Test processing stocks with bullish TQQQ signal."""
        mock_get_account.return_value = {'status': 'ACTIVE', 'buying_power': '197994.15'}
        mock_sell_all.return_value = [
            AlpacaOrder('SPY', 'SELL', 50, 425.0, 21250, 'order-1', 'new', 
                       datetime.now().isoformat(), 'Selling for TQQQ')
        ]
        mock_buy_tqqq.return_value = AlpacaOrder('TQQQ', 'BUY', 1000, 104.74, 104740,
                                                'order-2', 'new', datetime.now().isoformat(),
                                                'Buying TQQQ')
        
        market_signals = {
            'TQQQ': {
                'status': 'analyzed',
                'signal': 'bullish',
                'current_price': 110.0,
                'ema_10': 108.0,
                'ema_20': 106.0
            }
        }
        
        result = self.trader.process_all_stocks(market_signals)
        
        assert result['tqqq_signal'] == 'bullish'
        assert result['total_orders'] == 2  # 1 sell + 1 buy
        assert result['buys'] == 1
        assert result['sells'] == 1
        mock_sell_all.assert_called_once_with('TQQQ')
        mock_buy_tqqq.assert_called_once_with(110.0)
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_account')
    @patch('trading.alpaca_trader.AlpacaTrader.get_position')
    @patch('trading.alpaca_trader.AlpacaTrader.place_sell_order')
    def test_process_all_stocks_bearish_signal(self, mock_sell_order, mock_get_position, mock_get_account):
        """Test processing stocks with bearish TQQQ signal."""
        mock_get_account.return_value = {'status': 'ACTIVE', 'buying_power': '197994.15'}
        mock_get_position.return_value = {'qty': '100'}  # Has TQQQ position
        mock_sell_order.return_value = AlpacaOrder('TQQQ', 'SELL', 100, 104.74, 10474,
                                                  'order-3', 'new', datetime.now().isoformat(),
                                                  'Bearish signal')
        
        market_signals = {
            'TQQQ': {
                'status': 'analyzed',
                'signal': 'bearish',
                'current_price': 104.0,
                'ema_10': 106.0,
                'ema_20': 108.0
            }
        }
        
        result = self.trader.process_all_stocks(market_signals)
        
        assert result['tqqq_signal'] == 'bearish'
        assert result['total_orders'] == 1
        assert result['sells'] == 1
        mock_sell_order.assert_called_once()
    
    @patch('trading.alpaca_trader.AlpacaTrader.get_account')
    def test_process_all_stocks_neutral_signal(self, mock_get_account):
        """Test processing stocks with neutral TQQQ signal."""
        mock_get_account.return_value = {'status': 'ACTIVE', 'buying_power': '197994.15'}
        
        market_signals = {
            'TQQQ': {
                'status': 'analyzed',
                'signal': 'neutral',
                'current_price': 107.0,
                'ema_10': 106.0,
                'ema_20': 108.0
            }
        }
        
        result = self.trader.process_all_stocks(market_signals)
        
        assert result['tqqq_signal'] == 'neutral'
        assert result['total_orders'] == 0
        assert result['buys'] == 0
        assert result['sells'] == 0
    
    def test_process_all_stocks_no_account(self):
        """Test processing when cannot get account info."""
        with patch('trading.alpaca_trader.AlpacaTrader.get_account') as mock_get_account:
            mock_get_account.return_value = None
            
            market_signals = {'TQQQ': {'status': 'analyzed', 'signal': 'bullish'}}
            result = self.trader.process_all_stocks(market_signals)
            
            assert 'error' in result
            assert 'Could not connect to Alpaca' in result['error']