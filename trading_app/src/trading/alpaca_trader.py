"""
Alpaca trading integration for executing buy/sell orders.
Simple logic: Buy if price > 10 EMA > 20 EMA, sell otherwise.
"""

import json
import logging
import os
import boto3
import requests
from datetime import datetime
from typing import Dict, Optional, List, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from risk_management.stop_loss_strategy import StopLossStrategy

logger = logging.getLogger(__name__)


@dataclass
class AlpacaOrder:
    """Alpaca order result."""
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: int
    price: float
    amount: float
    order_id: str
    status: str
    timestamp: str
    reason: str
    stop_price: Optional[float] = None
    take_profit_price: Optional[float] = None


class AlpacaTrader:
    """Alpaca trading client with simple EMA strategy."""

    def __init__(self, paper_trading: bool = True, stop_loss_strategy: Optional['StopLossStrategy'] = None):
        """
        Initialize Alpaca trader.

        Args:
            paper_trading: Use paper trading (True) or live trading (False)
            stop_loss_strategy: Optional stop loss strategy for risk management
        """
        self.paper_trading = paper_trading
        self.base_url = "https://paper-api.alpaca.markets" if paper_trading else "https://api.alpaca.markets"
        self.api_key, self.secret_key = self._get_alpaca_credentials()
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }
        self.orders = []
        self.stop_loss_strategy = stop_loss_strategy

        if self.stop_loss_strategy:
            logger.info(f"Initialized with stop loss strategy: {self.stop_loss_strategy.get_strategy_name()}")
    
    def set_stop_loss_strategy(self, strategy: Optional['StopLossStrategy']) -> None:
        """
        Set or change the stop loss strategy at runtime.

        Args:
            strategy: Stop loss strategy to use, or None to disable
        """
        self.stop_loss_strategy = strategy
        if strategy:
            logger.info(f"Stop loss strategy updated: {strategy.get_strategy_name()}")
        else:
            logger.info("Stop loss strategy disabled")

    def _get_alpaca_credentials(self) -> tuple:
        """Get Alpaca API credentials from AWS Secrets Manager."""
        try:
            secrets_arn = os.environ.get('SECRETS_ARN')
            if not secrets_arn:
                logger.error("SECRETS_ARN environment variable not set")
                return None, None
            
            client = boto3.client('secretsmanager')
            response = client.get_secret_value(SecretId=secrets_arn)
            secrets = json.loads(response['SecretString'])
            
            api_key = secrets.get('alpaca_key_id')
            secret_key = secrets.get('alpaca_secret_key')
            
            if not api_key or not secret_key:
                logger.error("Alpaca credentials not found in secrets")
                return None, None
            
            logger.info("Successfully retrieved Alpaca credentials from Secrets Manager")
            return api_key, secret_key
            
        except Exception as e:
            logger.error(f"Error retrieving Alpaca credentials: {str(e)}")
            return None, None
    
    def get_account(self) -> Optional[Dict]:
        """Get Alpaca account information."""
        try:
            url = f"{self.base_url}/v2/account"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            account = response.json()
            logger.info(f"Account status: {account.get('status')}, Buying power: ${account.get('buying_power', 0)}")
            return account
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for a symbol."""
        try:
            url = f"{self.base_url}/v2/positions/{symbol}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 404:
                return None  # No position
            
            response.raise_for_status()
            position = response.json()
            
            logger.info(f"Position in {symbol}: {position.get('qty')} shares at ${position.get('avg_entry_price')}")
            return position
            
        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {str(e)}")
            return None
    
    def should_buy(self, symbol: str, price: float, ema_10: float, ema_20: float) -> tuple:
        """Check if we should buy: price > 10 EMA > 20 EMA and no existing position."""
        try:
            # Check market condition
            if not (price > ema_10 > ema_20):
                return False, f"No buy signal: Price ${price:.2f}, 10EMA ${ema_10:.2f}, 20EMA ${ema_20:.2f}"
            
            # Check if we already have a position
            position = self.get_position(symbol)
            if position and float(position.get('qty', 0)) > 0:
                return False, f"Already have position in {symbol}: {position.get('qty')} shares"
            
            return True, f"BUY signal: Price ${price:.2f} > 10EMA ${ema_10:.2f} > 20EMA ${ema_20:.2f}"
            
        except Exception as e:
            logger.error(f"Error in buy decision for {symbol}: {str(e)}")
            return False, f"Error in buy decision: {str(e)}"
    
    def should_sell(self, symbol: str, price: float, ema_10: float, ema_20: float) -> tuple:
        """Check if we should sell: NOT (price > 10 EMA > 20 EMA) and have position."""
        try:
            # Check if we have a position to sell
            position = self.get_position(symbol)
            if not position or float(position.get('qty', 0)) <= 0:
                return False, f"No position in {symbol} to sell"
            
            # Check if signal is broken
            if price > ema_10 > ema_20:
                return False, f"Hold position: Price ${price:.2f} > 10EMA ${ema_10:.2f} > 20EMA ${ema_20:.2f}"
            
            return True, f"SELL signal: Condition broken - Price ${price:.2f}, 10EMA ${ema_10:.2f}, 20EMA ${ema_20:.2f}"
            
        except Exception as e:
            logger.error(f"Error in sell decision for {symbol}: {str(e)}")
            return False, f"Error in sell decision: {str(e)}"
    
    def place_buy_order(self, symbol: str, price: float, reason: str, quantity: int = None, use_stop_loss: bool = True) -> Optional[AlpacaOrder]:
        """
        Place a buy order for specified quantity.

        Args:
            symbol: Stock ticker symbol
            price: Current market price (for estimation)
            reason: Reason for the order
            quantity: Number of shares to buy
            use_stop_loss: Whether to use stop loss strategy if available

        Returns:
            AlpacaOrder object or None if failed
        """
        try:
            if not self.api_key or not self.secret_key:
                logger.error("Alpaca credentials not available")
                return None

            if not quantity or quantity <= 0:
                logger.warning(f"Cannot buy {symbol}: invalid quantity {quantity}")
                return None

            order_data = {
                "symbol": symbol,
                "qty": str(quantity),
                "side": "buy",
                "type": "market",
                "time_in_force": "day"
            }

            # Calculate stop loss and take profit if strategy is set
            stop_price = None
            take_profit_price = None

            if use_stop_loss and self.stop_loss_strategy:
                try:
                    stop_price = self.stop_loss_strategy.calculate_stop_price(price, symbol)
                    take_profit_price = self.stop_loss_strategy.calculate_take_profit_price(price, symbol)

                    # Add bracket order parameters
                    order_data["order_class"] = "bracket"
                    order_data["stop_loss"] = {"stop_price": str(stop_price)}

                    if take_profit_price:
                        order_data["take_profit"] = {"limit_price": str(take_profit_price)}

                    logger.info(
                        f"{symbol}: Bracket order - Entry ${price:.2f}, "
                        f"Stop ${stop_price:.2f}, Target ${take_profit_price:.2f if take_profit_price else 'N/A'} "
                        f"({self.stop_loss_strategy.get_strategy_name()})"
                    )

                except Exception as e:
                    logger.error(f"Error calculating stop loss for {symbol}: {str(e)}")
                    # Continue with regular order if stop loss calculation fails

            url = f"{self.base_url}/v2/orders"
            response = requests.post(url, headers=self.headers, json=order_data, timeout=30)
            response.raise_for_status()

            order_result = response.json()

            alpaca_order = AlpacaOrder(
                symbol=symbol,
                action="BUY",
                quantity=quantity,
                price=price,
                amount=quantity * price,
                order_id=order_result.get('id'),
                status=order_result.get('status'),
                timestamp=datetime.now().isoformat(),
                reason=reason,
                stop_price=stop_price,
                take_profit_price=take_profit_price
            )

            self.orders.append(alpaca_order)

            order_type = "Bracket BUY" if stop_price else "BUY"
            logger.info(
                f"{order_type} order placed: {quantity} shares of {symbol} at ${price:.2f} "
                f"(Order ID: {alpaca_order.order_id})"
            )

            return alpaca_order

        except Exception as e:
            logger.error(f"Error placing buy order for {symbol}: {str(e)}")
            return None
    
    def place_sell_order(self, symbol: str, price: float, reason: str) -> Optional[AlpacaOrder]:
        """Place a sell order for entire position."""
        try:
            if not self.api_key or not self.secret_key:
                logger.error("Alpaca credentials not available")
                return None
            
            # Get current position
            position = self.get_position(symbol)
            if not position:
                logger.warning(f"No position in {symbol} to sell")
                return None
            
            quantity = int(float(position.get('qty', 0)))
            if quantity <= 0:
                logger.warning(f"No shares to sell for {symbol}")
                return None
            
            order_data = {
                "symbol": symbol,
                "qty": str(quantity),
                "side": "sell",
                "type": "market",
                "time_in_force": "day"
            }
            
            url = f"{self.base_url}/v2/orders"
            response = requests.post(url, headers=self.headers, json=order_data, timeout=30)
            response.raise_for_status()
            
            order_result = response.json()
            
            alpaca_order = AlpacaOrder(
                symbol=symbol,
                action="SELL",
                quantity=quantity,
                price=price,
                amount=quantity * price,
                order_id=order_result.get('id'),
                status=order_result.get('status'),
                timestamp=datetime.now().isoformat(),
                reason=reason
            )
            
            self.orders.append(alpaca_order)
            logger.info(f"SELL order placed: {quantity} shares of {symbol} at ${price:.2f} (Order ID: {alpaca_order.order_id})")
            return alpaca_order
            
        except Exception as e:
            logger.error(f"Error placing sell order for {symbol}: {str(e)}")
            return None
    
    def process_stock(self, symbol: str, signal_data: Dict) -> Optional[AlpacaOrder]:
        """Process a single stock and execute trade if needed."""
        try:
            if signal_data.get('status') != 'analyzed':
                logger.warning(f"No valid data for {symbol}")
                return None
            
            price = signal_data.get('current_price')
            ema_10 = signal_data.get('ema_10')
            ema_20 = signal_data.get('ema_20')
            
            if not all([price, ema_10, ema_20]):
                logger.warning(f"Missing price/EMA data for {symbol}")
                return None
            
            # Check sell first (risk management)
            should_sell, sell_reason = self.should_sell(symbol, price, ema_10, ema_20)
            if should_sell:
                return self.place_sell_order(symbol, price, sell_reason)
            
            # Check buy
            should_buy, buy_reason = self.should_buy(symbol, price, ema_10, ema_20)
            if should_buy:
                return self.place_buy_order(symbol, price, buy_reason)
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
            return None
    
    def sell_all_positions_except(self, exclude_symbol: str) -> List[AlpacaOrder]:
        """Sell all positions except the specified symbol."""
        executed_orders = []
        
        try:
            positions = self.get_all_positions()
            
            for position in positions:
                symbol = position.get('symbol')
                qty = float(position.get('qty', 0))
                
                # Skip if no quantity or if this is the symbol to exclude
                if qty <= 0 or symbol == exclude_symbol:
                    continue
                
                logger.info(f"Selling all {symbol} to make room for TQQQ")
                
                # Place market sell order for entire position
                order_data = {
                    "symbol": symbol,
                    "qty": str(int(qty)),
                    "side": "sell",
                    "type": "market",
                    "time_in_force": "day"
                }
                
                url = f"{self.base_url}/v2/orders"
                response = requests.post(url, headers=self.headers, json=order_data, timeout=30)
                response.raise_for_status()
                
                order_result = response.json()
                
                # Get current market price estimate
                current_price = float(position.get('market_value', 0)) / qty if qty > 0 else 0
                
                alpaca_order = AlpacaOrder(
                    symbol=symbol,
                    action="SELL",
                    quantity=int(qty),
                    price=current_price,
                    amount=int(qty) * current_price,
                    order_id=order_result.get('id'),
                    status=order_result.get('status'),
                    timestamp=datetime.now().isoformat(),
                    reason=f"Selling {symbol} to buy TQQQ (bullish signal)"
                )
                
                executed_orders.append(alpaca_order)
                self.orders.append(alpaca_order)
                logger.info(f"SELL order placed: {int(qty)} shares of {symbol} (Order ID: {alpaca_order.order_id})")
                
        except Exception as e:
            logger.error(f"Error selling positions: {str(e)}")
        
        return executed_orders
    
    def buy_tqqq_with_all_funds(self, tqqq_price: float) -> Optional[AlpacaOrder]:
        """
        Buy TQQQ with all available buying power.

        Uses stop loss strategy if configured.
        """
        try:
            # Get current account info for buying power
            account = self.get_account()
            if not account:
                return None

            buying_power = float(account.get('buying_power', 0))

            # Reserve small amount for market fluctuations
            available_cash = buying_power * 0.95  # Use 95% to avoid insufficient funds

            if available_cash < tqqq_price:
                logger.warning(f"Insufficient buying power: ${buying_power:.2f} available, TQQQ price ${tqqq_price:.2f}")
                return None

            # Calculate quantity
            quantity = int(available_cash / tqqq_price)

            if quantity <= 0:
                logger.warning(f"Cannot buy TQQQ: insufficient funds for even 1 share")
                return None

            logger.info(f"Buying {quantity} shares of TQQQ with ${available_cash:.2f} buying power")

            # Use place_buy_order which handles stop loss strategy
            return self.place_buy_order(
                symbol="TQQQ",
                price=tqqq_price,
                reason="Buying TQQQ with all available funds (bullish signal)",
                quantity=quantity,
                use_stop_loss=True
            )

        except Exception as e:
            logger.error(f"Error buying TQQQ with all funds: {str(e)}")
            return None
    
    def process_all_stocks(self, market_signals: Dict) -> Dict:
        """Process TQQQ signals and execute portfolio rebalancing strategy."""
        executed_orders = []
        
        logger.info(f"Processing TQQQ-focused strategy with Alpaca API")
        logger.info(f"Paper trading: {self.paper_trading}")
        
        # Get account info
        account = self.get_account()
        if not account:
            logger.error("Could not get Alpaca account info")
            return {"error": "Could not connect to Alpaca"}
        
        # Check TQQQ signal (should be the only symbol in market_signals)
        tqqq_signal = market_signals.get('TQQQ')
        if not tqqq_signal or tqqq_signal.get('status') != 'analyzed':
            logger.warning("No valid TQQQ signal data")
            return {"error": "No valid TQQQ signal"}
        
        tqqq_price = tqqq_signal.get('current_price')
        ema_10 = tqqq_signal.get('ema_10')
        ema_20 = tqqq_signal.get('ema_20')
        signal = tqqq_signal.get('signal')
        
        if not all([tqqq_price, ema_10, ema_20]):
            logger.warning("Missing TQQQ price/EMA data")
            return {"error": "Missing TQQQ data"}
        
        logger.info(f"TQQQ Signal: {signal} - Price ${tqqq_price:.2f}, 10h-EMA ${ema_10:.2f}, 20h-EMA ${ema_20:.2f}")
        
        if signal == 'bullish':
            # BULLISH: Sell everything except TQQQ, then buy TQQQ with all funds
            logger.info("TQQQ is BULLISH - Implementing portfolio concentration strategy")
            
            # Step 1: Sell all positions except TQQQ
            sell_orders = self.sell_all_positions_except('TQQQ')
            executed_orders.extend(sell_orders)
            
            # Step 2: Buy TQQQ with all available buying power
            # Note: We might need to wait a moment for sell orders to settle, but market orders are usually immediate
            tqqq_order = self.buy_tqqq_with_all_funds(tqqq_price)
            if tqqq_order:
                executed_orders.append(tqqq_order)
            
        elif signal == 'bearish':
            # BEARISH: Sell TQQQ if we have it
            logger.info("TQQQ is BEARISH - Checking if we need to sell TQQQ position")
            
            tqqq_position = self.get_position('TQQQ')
            if tqqq_position and float(tqqq_position.get('qty', 0)) > 0:
                sell_order = self.place_sell_order('TQQQ', tqqq_price, f"TQQQ bearish signal: Price ${tqqq_price:.2f} below EMAs")
                if sell_order:
                    executed_orders.append(sell_order)
            else:
                logger.info("No TQQQ position to sell")
        
        else:
            # NEUTRAL: No action needed
            logger.info("TQQQ signal is NEUTRAL - No trades executed")
        
        # Create summary
        buys = [o for o in executed_orders if o.action == "BUY"]
        sells = [o for o in executed_orders if o.action == "SELL"]
        
        summary = {
            "account_status": account.get('status'),
            "buying_power": float(account.get('buying_power', 0)),
            "tqqq_signal": signal,
            "tqqq_price": tqqq_price,
            "stop_loss_strategy": self.stop_loss_strategy.get_strategy_name() if self.stop_loss_strategy else "None",
            "total_orders": len(executed_orders),
            "buys": len(buys),
            "sells": len(sells),
            "buy_amount": sum(o.amount for o in buys),
            "sell_amount": sum(o.amount for o in sells),
            "orders": [
                {
                    "symbol": o.symbol,
                    "action": o.action,
                    "quantity": o.quantity,
                    "price": o.price,
                    "amount": o.amount,
                    "order_id": o.order_id,
                    "status": o.status,
                    "reason": o.reason,
                    "stop_price": o.stop_price,
                    "take_profit_price": o.take_profit_price
                }
                for o in executed_orders
            ],
            "paper_trading": self.paper_trading
        }
        
        logger.info(f"TQQQ strategy execution complete: {len(buys)} buys (${summary['buy_amount']:.2f}), {len(sells)} sells (${summary['sell_amount']:.2f})")
        
        return summary
    
    def get_all_positions(self) -> List[Dict]:
        """Get all current positions."""
        try:
            url = f"{self.base_url}/v2/positions"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            positions = response.json()
            logger.info(f"Current positions: {len(positions)}")
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []