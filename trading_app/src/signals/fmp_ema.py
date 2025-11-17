"""
EMA signal using Financial Modeling Prep API.
"""

import json
import logging
import os
import boto3
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from signals.base_signal import BaseSignal

logger = logging.getLogger(__name__)


class FMPEMASignal(BaseSignal):
    """EMA crossover signal using Financial Modeling Prep API."""
    
    def __init__(self):
        super().__init__("fmp_ema")
        self.api_key = self._get_fmp_api_key()
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    def _get_fmp_api_key(self) -> Optional[str]:
        """Get FMP API key from AWS Secrets Manager."""
        try:
            secrets_arn = os.environ.get('SECRETS_ARN')
            if not secrets_arn:
                logger.warning("SECRETS_ARN environment variable not set")
                return None
            
            client = boto3.client('secretsmanager')
            response = client.get_secret_value(SecretId=secrets_arn)
            secrets = json.loads(response['SecretString'])
            
            api_key = secrets.get('fmp_api_key')
            if api_key:
                logger.info("Successfully retrieved FMP API key from Secrets Manager")
                return api_key
            else:
                logger.warning("fmp_api_key not found in secrets")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving FMP API key: {str(e)}")
            return None
    
    def get_current_quote(self, symbol: str) -> Optional[float]:
        """Get current quote using historical daily data (most recent close)."""
        try:
            if not self.api_key:
                logger.error("FMP API key not available")
                return None
            
            # Try historical-price-full first (most common endpoint)
            url = f"{self.base_url}/historical-price-full/{symbol}"
            params = {
                'apikey': self.api_key,
                'limit': 1  # Just get the latest day
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'historical' in data and data['historical']:
                    latest = data['historical'][0]
                    price = latest.get('close')
                    if price:
                        logger.info(f"Current quote for {symbol}: ${price:.2f} (from historical data)")
                        return float(price)
            
            # Fallback to demo endpoint if available
            demo_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey=demo"
            demo_response = requests.get(demo_url, timeout=30)
            
            if demo_response.status_code == 200:
                demo_data = demo_response.json()
                if demo_data and isinstance(demo_data, list) and len(demo_data) > 0:
                    price = demo_data[0].get('price')
                    if price:
                        logger.info(f"Current quote for {symbol}: ${price:.2f} (from demo)")
                        return float(price)
            
            logger.error(f"Could not get current quote for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, days: int = 50) -> Optional[pd.DataFrame]:
        """Get historical daily data for a symbol."""
        try:
            if not self.api_key:
                logger.error("FMP API key not available")
                return None
            
            # Try with your API key first
            url = f"{self.base_url}/historical-price-full/{symbol}"
            params = {
                'apikey': self.api_key,
                'limit': days
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'historical' in data and data['historical']:
                    historical = data['historical']
                    
                    # Convert to DataFrame
                    df_data = []
                    for record in historical:
                        df_data.append({
                            'Date': pd.to_datetime(record['date']),
                            'Open': float(record['open']),
                            'High': float(record['high']),
                            'Low': float(record['low']),
                            'Close': float(record['close']),
                            'Volume': int(record['volume']) if record['volume'] else 0
                        })
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        df.set_index('Date', inplace=True)
                        df.sort_index(inplace=True)
                        
                        logger.info(f"Retrieved {len(df)} historical records for {symbol}")
                        return df
            
            # Fallback to demo endpoint for historical data
            demo_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey=demo"
            demo_response = requests.get(demo_url, timeout=30)
            
            if demo_response.status_code == 200:
                demo_data = demo_response.json()
                if demo_data and 'historical' in demo_data and demo_data['historical']:
                    historical = demo_data['historical'][:days]  # Limit to requested days
                    
                    df_data = []
                    for record in historical:
                        df_data.append({
                            'Date': pd.to_datetime(record['date']),
                            'Open': float(record['open']),
                            'High': float(record['high']),
                            'Low': float(record['low']),
                            'Close': float(record['close']),
                            'Volume': int(record['volume']) if record['volume'] else 0
                        })
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        df.set_index('Date', inplace=True)
                        df.sort_index(inplace=True)
                        
                        logger.info(f"Retrieved {len(df)} demo historical records for {symbol}")
                        return df
            
            logger.error(f"Could not get historical data for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        try:
            ema = data.ewm(span=period, adjust=False).mean()
            logger.info(f"Calculated {period}-period EMA using FMP data")
            return ema
        except Exception as e:
            logger.error(f"Error calculating {period}-period EMA: {str(e)}")
            return pd.Series()
    
    def analyze(self, symbol: str) -> Optional[Dict]:
        """
        Analyze a single stock using FMP data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with signal analysis or None if error
        """
        try:
            if not self.api_key:
                return {"status": "error", "message": "FMP API key not available"}
            
            # Get current price
            current_price = self.get_current_quote(symbol)
            if current_price is None:
                return {"status": "no_data"}
            
            # Get historical data
            historical_data = self.get_historical_data(symbol)
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
                "data_source": "financial_modeling_prep",
                "data_points": len(historical_data),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"FMP EMA analysis for {symbol}: {signal} signal - "
                       f"Price=${current_price:.2f}, 10EMA=${latest_ema_10:.2f}, 20EMA=${latest_ema_20:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with FMP: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def analyze_multiple(self, symbols: List[str]) -> Dict:
        """
        Analyze multiple stocks using FMP data.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with results for each symbol
        """
        results = {}
        
        logger.info(f"Analyzing {len(symbols)} symbols with FMP EMA signal")
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"Processing {symbol} ({i}/{len(symbols)}) with FMP")
                results[symbol] = self.analyze(symbol)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                results[symbol] = {"status": "error", "message": str(e)}
        
        return results
    
    def get_multiple_quotes(self, symbols: List[str]) -> Optional[Dict]:
        """Get quotes for multiple symbols in a single API call."""
        try:
            if not self.api_key:
                return None
            
            # FMP supports batch quotes
            symbols_str = ','.join(symbols)
            url = f"{self.base_url}/quote-short/{symbols_str}"
            params = {'apikey': self.api_key}
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or not isinstance(data, list):
                logger.error("No batch quote data received")
                return None
            
            results = {}
            for quote in data:
                symbol = quote.get('symbol')
                price = quote.get('price')
                if symbol and price is not None:
                    results[symbol] = float(price)
            
            logger.info(f"Retrieved batch quotes for {len(results)} symbols")
            return results
            
        except Exception as e:
            logger.error(f"Error getting batch quotes: {str(e)}")
            return None