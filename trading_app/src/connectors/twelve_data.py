"""
Twelve Data connector for fetching stock market data and calculating technical indicators.
Free tier: 800 API calls/day - perfect for 30 stocks every 2 hours (360 calls/day).
"""

import requests
import json
import pandas as pd
import numpy as np
import boto3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
import os

logger = logging.getLogger(__name__)


class TwelveDataConnector:
    """Handles market data fetching using Twelve Data API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Twelve Data connector.
        
        Args:
            api_key: Twelve Data API key (can also be set via environment variable or AWS Secrets Manager)
        """
        self.api_key = api_key or self._get_api_key_from_secrets() or os.environ.get('TWELVE_DATA_API_KEY', 'demo')
        self.base_url = "https://api.twelvedata.com"
    
    def _get_api_key_from_secrets(self) -> Optional[str]:
        """
        Get Twelve Data API key from AWS Secrets Manager.
        
        Returns:
            API key string or None if not found
        """
        try:
            secrets_arn = os.environ.get('SECRETS_ARN')
            if not secrets_arn:
                logger.warning("SECRETS_ARN environment variable not set")
                return None
            
            # Create a Secrets Manager client
            session = boto3.session.Session()
            client = session.client('secretsmanager')
            
            # Get the secret value
            response = client.get_secret_value(SecretId=secrets_arn)
            secrets = json.loads(response['SecretString'])
            
            api_key = secrets.get('twelve_data_api_key')
            if api_key:
                logger.info("Successfully retrieved Twelve Data API key from Secrets Manager")
                return api_key
            else:
                logger.warning("twelve_data_api_key not found in secrets")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving API key from Secrets Manager: {str(e)}")
            return None
        
    def get_stock_data(self, symbol: str, interval: str = "1day", outputsize: int = 60) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            interval: Time interval (1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month)
            outputsize: Number of data points (max 5000 for free tier)
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            url = f"{self.base_url}/time_series"
            params = {
                'symbol': symbol,
                'interval': interval,
                'outputsize': outputsize,
                'apikey': self.api_key,
                'format': 'JSON'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'status' in data and data['status'] == 'error':
                logger.error(f"Twelve Data error for {symbol}: {data.get('message', 'Unknown error')}")
                return None
                
            if 'values' not in data:
                logger.error(f"No values found in response for {symbol}")
                return None
            
            # Convert to DataFrame
            values = data['values']
            df_data = []
            
            for item in values:
                df_data.append({
                    'Date': pd.to_datetime(item['datetime']),
                    'Open': float(item['open']),
                    'High': float(item['high']),
                    'Low': float(item['low']),
                    'Close': float(item['close']),
                    'Volume': int(item['volume']) if item['volume'] else 0
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
            
            logger.info(f"Successfully fetched {len(df)} data points for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get real-time price quote.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Current price or None if error
        """
        try:
            url = f"{self.base_url}/price"
            params = {
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'status' in data and data['status'] == 'error':
                logger.error(f"Twelve Data price error for {symbol}: {data.get('message', 'Unknown error')}")
                return None
                
            if 'price' not in data:
                logger.error(f"No price data found for {symbol}")
                return None
                
            current_price = float(data['price'])
            logger.info(f"Current price for {symbol}: ${current_price}")
            return current_price
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return None
    
    def get_technical_indicator(self, symbol: str, indicator: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        Get technical indicators from Twelve Data API.
        
        Args:
            symbol: Stock ticker symbol
            indicator: Technical indicator (ema, sma, rsi, etc.)
            **kwargs: Additional parameters for the indicator
            
        Returns:
            DataFrame with indicator values or None if error
        """
        try:
            url = f"{self.base_url}/{indicator}"
            params = {
                'symbol': symbol,
                'apikey': self.api_key,
                'format': 'JSON',
                **kwargs
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'status' in data and data['status'] == 'error':
                logger.error(f"Twelve Data {indicator} error for {symbol}: {data.get('message', 'Unknown error')}")
                return None
                
            if 'values' not in data:
                logger.error(f"No {indicator} values found for {symbol}")
                return None
            
            # Convert to DataFrame
            values = data['values']
            df_data = []
            
            for item in values:
                df_data.append({
                    'Date': pd.to_datetime(item['datetime']),
                    indicator.upper(): float(item[indicator])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
            
            logger.info(f"Successfully fetched {indicator} for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {indicator} for {symbol}: {str(e)}")
            return None
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average locally.
        
        Args:
            data: Price data series (typically Close prices)
            period: Number of periods for EMA calculation
            
        Returns:
            Series with EMA values
        """
        try:
            ema = data.ewm(span=period, adjust=False).mean()
            logger.info(f"Calculated {period}-period EMA locally")
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating {period}-period EMA: {str(e)}")
            return pd.Series()
    
    def get_stock_indicators(self, symbol: str) -> Optional[Dict]:
        """
        Get current stock price, 10 EMA, and 20 EMA using Twelve Data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with price and indicator data or None if error
        """
        try:
            # Get current price (1 API call)
            current_price = self.get_current_price(symbol)
            if current_price is None:
                logger.error(f"Failed to get current price for {symbol}")
                return None
            
            # Get hourly historical data for EMA calculation (1 API call)
            # Get more data points for hourly EMAs (10 EMA = 10 hours, 20 EMA = 20 hours)
            # Request 30 hours to ensure we have enough data even with market gaps
            data = self.get_stock_data(symbol, interval="1h", outputsize=30)
            if data is None or data.empty:
                logger.error(f"Failed to get hourly historical data for {symbol}")
                return None
            
            # Calculate EMAs locally to save API calls
            close_prices = data['Close']
            ema_10 = self.calculate_ema(close_prices, 10)  # 10 hours
            ema_20 = self.calculate_ema(close_prices, 20)  # 20 hours
            
            # Get latest EMA values
            latest_ema_10 = float(ema_10.iloc[-1]) if not ema_10.empty else None
            latest_ema_20 = float(ema_20.iloc[-1]) if not ema_20.empty else None
            
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'ema_10': latest_ema_10,
                'ema_20': latest_ema_20,
                'timestamp': datetime.now().isoformat(),
                'data_points': len(data),
                'data_source': 'twelve_data_hourly',
                'timeframe': '1h',
                'ema_periods': '10h/20h',
                'api_calls_used': 2  # 1 for price + 1 for historical data
            }
            
            logger.info(f"Hourly EMA for {symbol}: Price=${current_price:.2f}, "
                       f"10h-EMA=${latest_ema_10:.2f}, 20h-EMA=${latest_ema_20:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting stock indicators for {symbol}: {str(e)}")
            return None
    
    def get_multiple_stocks_indicators(self, symbols: List[str]) -> Dict:
        """
        Get indicators for multiple stocks efficiently.
        Uses 2 API calls per stock (price + historical data).
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with results for each symbol
        """
        results = {}
        total_api_calls = 0
        
        logger.info(f"Processing {len(symbols)} symbols using Twelve Data API")
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"Processing {symbol} ({i}/{len(symbols)})")
                indicators = self.get_stock_indicators(symbol)
                results[symbol] = indicators
                
                if indicators:
                    total_api_calls += indicators.get('api_calls_used', 2)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                results[symbol] = None
        
        logger.info(f"Completed processing {len(symbols)} symbols. Total API calls used: {total_api_calls}")
        return results
    
    def get_batch_prices(self, symbols: List[str]) -> Optional[Dict]:
        """
        Get multiple stock prices in a single API call (if supported).
        
        Args:
            symbols: List of stock ticker symbols (max 8 for free tier)
            
        Returns:
            Dictionary with symbol -> price mapping
        """
        try:
            if len(symbols) > 8:
                logger.warning("Twelve Data free tier supports max 8 symbols in batch. Splitting request.")
                # Split into chunks and process separately
                results = {}
                for i in range(0, len(symbols), 8):
                    chunk = symbols[i:i+8]
                    chunk_results = self.get_batch_prices(chunk)
                    if chunk_results:
                        results.update(chunk_results)
                return results
            
            url = f"{self.base_url}/price"
            params = {
                'symbol': ','.join(symbols),
                'apikey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle batch response format
            if isinstance(data, dict) and 'status' in data and data['status'] == 'error':
                logger.error(f"Twelve Data batch price error: {data.get('message', 'Unknown error')}")
                return None
            
            results = {}
            if isinstance(data, dict):
                # Multiple symbols response
                for symbol, price_data in data.items():
                    if isinstance(price_data, dict) and 'price' in price_data:
                        results[symbol] = float(price_data['price'])
                    else:
                        logger.warning(f"Invalid price data for {symbol}")
            
            logger.info(f"Successfully fetched batch prices for {len(results)} symbols")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching batch prices: {str(e)}")
            return None