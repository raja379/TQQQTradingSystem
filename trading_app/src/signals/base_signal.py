"""
Base signal class for trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime


class BaseSignal(ABC):
    """Base class for all trading signals."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def analyze(self, symbol: str) -> Optional[Dict]:
        """
        Analyze a stock and return signal data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with signal analysis or None if error
        """
        pass
    
    @abstractmethod
    def analyze_multiple(self, symbols: List[str]) -> Dict:
        """
        Analyze multiple stocks.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with results for each symbol
        """
        pass
    
    def get_signal_type(self, price: float, ema_10: float, ema_20: float) -> str:
        """
        Determine signal type based on EMA crossover.
        
        Args:
            price: Current stock price
            ema_10: 10-period EMA
            ema_20: 20-period EMA
            
        Returns:
            Signal type: 'bullish', 'bearish', or 'neutral'
        """
        if price > ema_10 > ema_20:
            return "bullish"
        elif price < ema_10 < ema_20:
            return "bearish"
        else:
            return "neutral"