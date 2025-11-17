"""
EMA signal using Twelve Data API.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from signals.base_signal import BaseSignal
from connectors.twelve_data import TwelveDataConnector

logger = logging.getLogger(__name__)


class TwelveDataEMASignal(BaseSignal):
    """EMA crossover signal using Twelve Data API."""
    
    def __init__(self):
        super().__init__("twelve_data_ema")
        self.connector = TwelveDataConnector()
    
    def analyze(self, symbol: str) -> Optional[Dict]:
        """
        Analyze a single stock using Twelve Data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with signal analysis or None if error
        """
        try:
            # Get stock indicators from Twelve Data
            data = self.connector.get_stock_indicators(symbol)
            if not data:
                return {"status": "no_data"}
            
            price = data['current_price']
            ema_10 = data['ema_10']
            ema_20 = data['ema_20']
            
            if not all([price, ema_10, ema_20]):
                return {"status": "insufficient_data"}
            
            signal = self.get_signal_type(price, ema_10, ema_20)
            
            return {
                "status": "analyzed",
                "signal": signal,
                "current_price": price,
                "ema_10": ema_10,
                "ema_20": ema_20,
                "ema_spread": ema_10 - ema_20,
                "data_source": "twelve_data",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with Twelve Data: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def analyze_multiple(self, symbols: List[str]) -> Dict:
        """
        Analyze multiple stocks using Twelve Data.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with results for each symbol
        """
        results = {}
        
        logger.info(f"Analyzing {len(symbols)} symbols with Twelve Data EMA signal")
        
        for symbol in symbols:
            try:
                results[symbol] = self.analyze(symbol)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                results[symbol] = {"status": "error", "message": str(e)}
        
        return results