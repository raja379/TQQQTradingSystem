"""
Abstract base class for stop loss strategies.
Implements the Strategy pattern to allow pluggable stop loss calculation methods.
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class StopLossStrategy(ABC):
    """
    Abstract base class for stop loss strategies.

    This interface allows different stop loss calculation methods to be plugged
    into the trading system. Subclasses should implement specific strategies like
    percentage-based, ATR-based, technical level-based, or time-based stops.

    Example usage:
        strategy = PercentageStopLoss(stop_loss_pct=0.05)
        stop_price = strategy.calculate_stop_price(entry_price=100.0, symbol="TQQQ")
        # stop_price would be 95.0 (5% below entry)
    """

    @abstractmethod
    def calculate_stop_price(self, entry_price: float, symbol: str) -> float:
        """
        Calculate the stop loss price for a position.

        Args:
            entry_price: The entry price of the position
            symbol: The stock ticker symbol (e.g., "TQQQ")

        Returns:
            The calculated stop loss price

        Raises:
            ValueError: If entry_price is invalid or calculation fails
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get a descriptive name for this strategy.

        Returns:
            Human-readable strategy name (e.g., "Percentage-Based (5%)")
        """
        pass

    def calculate_take_profit_price(self, entry_price: float, symbol: str) -> Optional[float]:
        """
        Calculate the take profit price for a position (optional).

        This method is optional and returns None by default. Strategies can override
        this to implement profit targets (e.g., using reward:risk ratios).

        Args:
            entry_price: The entry price of the position
            symbol: The stock ticker symbol

        Returns:
            The calculated take profit price, or None if not applicable
        """
        return None

    def validate(self) -> bool:
        """
        Validate that the strategy parameters are valid.

        This method can be overridden by subclasses to perform parameter validation.
        Should raise ValueError if parameters are invalid.

        Returns:
            True if parameters are valid

        Raises:
            ValueError: If parameters are invalid
        """
        return True

    def __str__(self) -> str:
        """String representation of the strategy."""
        return self.get_strategy_name()
