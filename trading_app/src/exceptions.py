"""
Custom exceptions for the trading system.
"""


class TradingSystemError(Exception):
    """Base exception for trading system errors."""
    pass


class DataFetchError(TradingSystemError):
    """Exception raised when data fetching fails."""
    pass


class CalculationError(TradingSystemError):
    """Exception raised when calculations fail."""
    pass


class TradeExecutionError(TradingSystemError):
    """Exception raised when trade execution fails."""
    pass


class ConfigurationError(TradingSystemError):
    """Exception raised when configuration is invalid."""
    pass