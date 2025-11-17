"""
EMA signal using Alpaca Market Data API.
"""

import json
import logging
import os
import boto3
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from .base_signal import BaseSignal

logger = logging.getLogger(__name__)


class AlpacaEMASignal(BaseSignal):
    """EMA crossover signal using Alpaca Market Data API."""
    
    def __init__(self, paper_trading: bool = True):
        super().__init__("alpaca_ema")
        self.paper_trading = paper_trading
        self.base_url = "https://paper-api.alpaca.markets" if paper_trading else "https://api.alpaca.markets"
        self.data_url = "https://data.alpaca.markets"
        self.api_key, self.secret_key = self._get_alpaca_credentials()
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }
    
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
    
    def get_latest_quote(self, symbol: str) -> Optional[float]:
        """Get latest quote for a symbol."""
        try:
            url = f"{self.data_url}/v2/stocks/{symbol}/quotes/latest"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            quote = data.get('quote', {})
            
            # Use bid-ask midpoint or ask price
            bid = quote.get('bp', 0)
            ask = quote.get('ap', 0)
            
            if bid and ask:
                price = (bid + ask) / 2
            elif ask:
                price = ask
            elif bid:
                price = bid
            else:
                logger.warning(f"No bid/ask data for {symbol}")
                return None
            
            logger.info(f"Latest quote for {symbol}: ${price:.2f}")
            return price
            
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {str(e)}")
            return None
    
    def get_historical_bars(self, symbol: str, days: int = 50) -> Optional[pd.DataFrame]:
        """Get historical daily bars for a symbol."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # Extra buffer for weekends
            
            url = f"{self.data_url}/v2/stocks/{symbol}/bars"
            params = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'timeframe': '1Day',
                'limit': days
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            bars = data.get('bars', [])
            
            if not bars:
                logger.error(f"No historical data found for {symbol}")
                return None
            
            # Convert to DataFrame
            df_data = []
            for bar in bars:
                df_data.append({
                    'Date': pd.to_datetime(bar['t']),
                    'Open': float(bar['o']),
                    'High': float(bar['h']),
                    'Low': float(bar['l']),
                    'Close': float(bar['c']),
                    'Volume': int(bar['v'])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
            
            logger.info(f"Retrieved {len(df)} historical bars for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        try:
            ema = data.ewm(span=period, adjust=False).mean()
            logger.info(f"Calculated {period}-period EMA")
            return ema
        except Exception as e:
            logger.error(f"Error calculating {period}-period EMA: {str(e)}")
            return pd.Series()
    
    def analyze(self, symbol: str) -> Optional[Dict]:
        """
        Analyze a single stock using Alpaca data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with signal analysis or None if error
        """
        try:
            if not self.api_key or not self.secret_key:
                return {"status": "error", "message": "Alpaca credentials not available"}
            
            # Get current price
            current_price = self.get_latest_quote(symbol)
            if current_price is None:
                return {"status": "no_data"}
            
            # Get historical data
            historical_data = self.get_historical_bars(symbol)
            if historical_data is None or historical_data.empty:
                return {"status": "no_data"}
            
            # Calculate EMAs
            close_prices = historical_data['Close']
            ema_10 = self.calculate_ema(close_prices, 10)
            ema_20 = self.calculate_ema(close_prices, 20)
            
            # Get latest EMA values
            latest_ema_10 = float(ema_10.iloc[-1]) if not ema_10.empty else None
            latest_ema_20 = float(ema_20.iloc[-1]) if not ema_20.empty else None
            
            if not all([current_price, latest_ema_10, latest_ema_20]):
                return {"status": "insufficient_data"}
            
            signal = self.get_signal_type(current_price, latest_ema_10, latest_ema_20)
            
            result = {
                "status": "analyzed",
                "signal": signal,
                "current_price": current_price,
                "ema_10": latest_ema_10,
                "ema_20": latest_ema_20,
                "ema_spread": latest_ema_10 - latest_ema_20,
                "data_source": "alpaca",
                "data_points": len(historical_data),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Alpaca EMA analysis for {symbol}: {signal} signal - "
                       f"Price=${current_price:.2f}, 10EMA=${latest_ema_10:.2f}, 20EMA=${latest_ema_20:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with Alpaca: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def analyze_multiple(self, symbols: List[str]) -> Dict:
        """
        Analyze multiple stocks using Alpaca data.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with results for each symbol
        """
        results = {}
        
        logger.info(f"Analyzing {len(symbols)} symbols with Alpaca EMA signal")
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"Processing {symbol} ({i}/{len(symbols)}) with Alpaca")
                results[symbol] = self.analyze(symbol)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                results[symbol] = {"status": "error", "message": str(e)}
        
        return results