"""
Integration tests for end-to-end trading workflow.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from signals.twelve_data_ema import TwelveDataEMASignal
from trading.alpaca_trader import AlpacaTrader


class TestTradingWorkflowIntegration:
    """Integration tests for complete trading workflow."""
    
    @patch('connectors.twelve_data.TwelveDataConnector._get_api_key_from_secrets')
    @patch('trading.alpaca_trader.AlpacaTrader._get_alpaca_credentials')
    @patch('requests.get')
    @patch('requests.post')
    def test_bullish_signal_to_trade_execution(self, mock_post, mock_get, 
                                               mock_alpaca_creds, mock_twelve_creds):
        """Test complete workflow from bullish signal to trade execution."""
        # Setup mocks
        mock_twelve_creds.return_value = 'test_twelve_key'
        mock_alpaca_creds.return_value = ('test_alpaca_key', 'test_alpaca_secret')
        
        # Mock Twelve Data responses
        def get_side_effect(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()
            
            if 'price' in url:
                response.json.return_value = {'price': '110.50'}
            elif 'time_series' in url:
                response.json.return_value = {
                    'values': [
                        {
                            'datetime': f'2025-11-17 {14+i}:30:00',
                            'open': f'{108.0 + i*0.1}',
                            'high': f'{108.5 + i*0.1}',
                            'low': f'{107.5 + i*0.1}',
                            'close': f'{108.2 + i*0.1}',
                            'volume': '1000000'
                        }
                        for i in range(30)
                    ]
                }
            return response
        
        mock_get.side_effect = get_side_effect
        
        # Mock Alpaca responses
        def post_side_effect(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()
            response.json.return_value = {
                'id': 'test-order-123',
                'status': 'new'
            }
            return response
        
        # Mock Alpaca GET requests (account, positions)
        def alpaca_get_side_effect(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()
            
            if 'account' in url:
                response.json.return_value = {
                    'status': 'ACTIVE',
                    'buying_power': '200000.00'
                }
            elif 'positions' in url:
                if url.endswith('positions'):
                    # All positions
                    response.json.return_value = [
                        {'symbol': 'SPY', 'qty': '50', 'market_value': '21250'},
                        {'symbol': 'QQQ', 'qty': '25', 'market_value': '12500'}
                    ]
                else:
                    # Single position lookup (404 for TQQQ)
                    response.status_code = 404
            
            return response
        
        # Apply mocks based on URL patterns
        def combined_get_side_effect(url, **kwargs):
            if 'twelvedata' in url:
                return get_side_effect(url, **kwargs)
            elif 'alpaca' in url:
                return alpaca_get_side_effect(url, **kwargs)
            else:
                return get_side_effect(url, **kwargs)
        
        mock_get.side_effect = combined_get_side_effect
        mock_post.side_effect = post_side_effect
        
        # Execute workflow
        signal_analyzer = TwelveDataEMASignal()
        trader = AlpacaTrader(paper_trading=True)
        
        # Analyze signals
        signals = signal_analyzer.analyze_multiple(['TQQQ'])
        
        # Execute trades
        trading_results = trader.process_all_stocks(signals)
        
        # Assertions
        assert signals['TQQQ']['status'] == 'analyzed'
        assert signals['TQQQ']['signal'] == 'bullish'
        assert signals['TQQQ']['current_price'] == 110.50
        
        # Should have executed trades (sells + buy)
        assert trading_results['total_orders'] > 0
        assert trading_results['tqqq_signal'] == 'bullish'
        
        # Verify API calls were made
        assert mock_get.call_count >= 2  # Price + historical data
        assert mock_post.call_count >= 1  # Trade orders
    
    @patch('connectors.twelve_data.TwelveDataConnector._get_api_key_from_secrets')
    @patch('trading.alpaca_trader.AlpacaTrader._get_alpaca_credentials')
    @patch('requests.get')
    @patch('requests.post')
    def test_bearish_signal_no_position(self, mock_post, mock_get, 
                                        mock_alpaca_creds, mock_twelve_creds):
        """Test bearish signal when no TQQQ position exists."""
        # Setup mocks
        mock_twelve_creds.return_value = 'test_twelve_key'
        mock_alpaca_creds.return_value = ('test_alpaca_key', 'test_alpaca_secret')
        
        # Mock bearish signal data
        def get_side_effect(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()
            
            if 'price' in url:
                response.json.return_value = {'price': '104.00'}
            elif 'time_series' in url:
                response.json.return_value = {
                    'values': [
                        {
                            'datetime': f'2025-11-17 {14+i}:30:00',
                            'open': f'{106.0 - i*0.1}',
                            'high': f'{106.5 - i*0.1}',
                            'low': f'{105.5 - i*0.1}',
                            'close': f'{106.2 - i*0.1}',
                            'volume': '1000000'
                        }
                        for i in range(30)
                    ]
                }
            elif 'account' in url:
                response.json.return_value = {
                    'status': 'ACTIVE',
                    'buying_power': '200000.00'
                }
            elif 'positions' in url and 'TQQQ' in url:
                # No TQQQ position
                response.status_code = 404
            
            return response
        
        mock_get.side_effect = get_side_effect
        
        # Execute workflow
        signal_analyzer = TwelveDataEMASignal()
        trader = AlpacaTrader(paper_trading=True)
        
        signals = signal_analyzer.analyze_multiple(['TQQQ'])
        trading_results = trader.process_all_stocks(signals)
        
        # Assertions
        assert signals['TQQQ']['signal'] == 'bearish'
        assert trading_results['total_orders'] == 0  # No trades executed
        assert trading_results['sells'] == 0
        assert mock_post.call_count == 0  # No orders placed
    
    @patch('connectors.twelve_data.TwelveDataConnector._get_api_key_from_secrets')
    @patch('trading.alpaca_trader.AlpacaTrader._get_alpaca_credentials')
    @patch('requests.get')
    def test_api_error_handling(self, mock_get, mock_alpaca_creds, mock_twelve_creds):
        """Test handling of API errors in workflow."""
        # Setup mocks
        mock_twelve_creds.return_value = 'test_twelve_key'
        mock_alpaca_creds.return_value = ('test_alpaca_key', 'test_alpaca_secret')
        
        # Mock API error
        def get_side_effect(url, **kwargs):
            response = Mock()
            response.raise_for_status.side_effect = Exception("API rate limit exceeded")
            return response
        
        mock_get.side_effect = get_side_effect
        
        # Execute workflow
        signal_analyzer = TwelveDataEMASignal()
        signals = signal_analyzer.analyze_multiple(['TQQQ'])
        
        # Should handle error gracefully
        assert signals['TQQQ']['status'] == 'error'
        assert 'API rate limit exceeded' in signals['TQQQ']['message']
    
    @patch('connectors.twelve_data.TwelveDataConnector._get_api_key_from_secrets')
    @patch('trading.alpaca_trader.AlpacaTrader._get_alpaca_credentials')
    @patch('requests.get')
    def test_neutral_signal_no_action(self, mock_get, mock_alpaca_creds, mock_twelve_creds):
        """Test neutral signal results in no trading action."""
        # Setup mocks
        mock_twelve_creds.return_value = 'test_twelve_key'
        mock_alpaca_creds.return_value = ('test_alpaca_key', 'test_alpaca_secret')
        
        # Mock neutral signal data (price between EMAs)
        def get_side_effect(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()
            
            if 'price' in url:
                response.json.return_value = {'price': '107.00'}
            elif 'time_series' in url:
                response.json.return_value = {
                    'values': [
                        {
                            'datetime': f'2025-11-17 {14+i}:30:00',
                            'open': f'{106.0 + (i%3)*0.1}',
                            'high': f'{106.5 + (i%3)*0.1}',
                            'low': f'{105.5 + (i%3)*0.1}',
                            'close': f'{106.2 + (i%3)*0.1}',
                            'volume': '1000000'
                        }
                        for i in range(30)
                    ]
                }
            elif 'account' in url:
                response.json.return_value = {
                    'status': 'ACTIVE',
                    'buying_power': '200000.00'
                }
            
            return response
        
        mock_get.side_effect = get_side_effect
        
        # Execute workflow
        signal_analyzer = TwelveDataEMASignal()
        trader = AlpacaTrader(paper_trading=True)
        
        signals = signal_analyzer.analyze_multiple(['TQQQ'])
        trading_results = trader.process_all_stocks(signals)
        
        # Assertions
        assert signals['TQQQ']['signal'] == 'neutral'
        assert trading_results['total_orders'] == 0