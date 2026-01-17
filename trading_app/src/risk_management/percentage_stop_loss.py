"""
Percentage-based stop loss strategy implementation.
"""

from typing import Optional
from dataclasses import dataclass
import logging

from src.risk_management.stop_loss_strategy import StopLossStrategy

logger = logging.getLogger(__name__)


@dataclass
class PercentageStopLoss(StopLossStrategy):
    """
    Percentage-based stop loss strategy.

    Calculates stop loss as a fixed percentage below the entry price.
    Optionally calculates take profit as a fixed percentage above entry price.

    Example:
        # 5% stop loss, 15% take profit (3:1 reward:risk)
        strategy = PercentageStopLoss(
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )

        entry = 100.0
        stop = strategy.calculate_stop_price(entry, "TQQQ")  # Returns 95.0
        target = strategy.calculate_take_profit_price(entry, "TQQQ")  # Returns 115.0

    Attributes:
        stop_loss_pct: Percentage below entry for stop (e.g., 0.05 for 5%)
        take_profit_pct: Optional percentage above entry for profit target
        min_stop_distance: Optional minimum dollar distance for stop (e.g., 1.0)
        max_stop_distance: Optional maximum dollar distance for stop
    """

    stop_loss_pct: float
    take_profit_pct: Optional[float] = None
    min_stop_distance: Optional[float] = None
    max_stop_distance: Optional[float] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()

    def calculate_stop_price(self, entry_price: float, symbol: str) -> float:
        """
        Calculate the stop loss price based on percentage.

        Args:
            entry_price: The entry price of the position
            symbol: The stock ticker symbol

        Returns:
            The calculated stop loss price, rounded to 2 decimals

        Raises:
            ValueError: If entry_price is invalid
        """
        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")

        # Calculate stop distance
        stop_distance = entry_price * self.stop_loss_pct

        # Apply min/max constraints if specified
        if self.min_stop_distance is not None and stop_distance < self.min_stop_distance:
            logger.info(
                f"{symbol}: Stop distance ${stop_distance:.2f} below minimum ${self.min_stop_distance:.2f}, "
                f"using minimum"
            )
            stop_distance = self.min_stop_distance

        if self.max_stop_distance is not None and stop_distance > self.max_stop_distance:
            logger.info(
                f"{symbol}: Stop distance ${stop_distance:.2f} above maximum ${self.max_stop_distance:.2f}, "
                f"using maximum"
            )
            stop_distance = self.max_stop_distance

        stop_price = entry_price - stop_distance

        logger.info(
            f"{symbol}: Calculated stop price ${stop_price:.2f} "
            f"({self.stop_loss_pct * 100:.1f}% below entry ${entry_price:.2f})"
        )

        return round(stop_price, 2)

    def calculate_take_profit_price(self, entry_price: float, symbol: str) -> Optional[float]:
        """
        Calculate the take profit price based on percentage.

        Args:
            entry_price: The entry price of the position
            symbol: The stock ticker symbol

        Returns:
            The calculated take profit price, or None if not configured
        """
        if self.take_profit_pct is None:
            return None

        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")

        target_price = entry_price * (1 + self.take_profit_pct)

        logger.info(
            f"{symbol}: Calculated take profit ${target_price:.2f} "
            f"({self.take_profit_pct * 100:.1f}% above entry ${entry_price:.2f})"
        )

        return round(target_price, 2)

    def get_strategy_name(self) -> str:
        """
        Get a descriptive name for this strategy.

        Returns:
            Strategy name with percentage (e.g., "Percentage-Based (5%)")
        """
        name = f"Percentage-Based ({self.stop_loss_pct * 100:.1f}%)"
        if self.take_profit_pct is not None:
            reward_risk = self.take_profit_pct / self.stop_loss_pct
            name += f" [R:R {reward_risk:.1f}:1]"
        return name

    def validate(self) -> bool:
        """
        Validate strategy parameters.

        Returns:
            True if valid

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate stop loss percentage
        if not 0.001 <= self.stop_loss_pct <= 0.5:
            raise ValueError(
                f"stop_loss_pct must be between 0.001 and 0.5 (0.1% to 50%), "
                f"got {self.stop_loss_pct}"
            )

        # Validate take profit percentage if specified
        if self.take_profit_pct is not None and self.take_profit_pct <= 0:
            raise ValueError(
                f"take_profit_pct must be positive, got {self.take_profit_pct}"
            )

        # Validate min/max constraints
        if (
            self.min_stop_distance is not None
            and self.max_stop_distance is not None
            and self.min_stop_distance > self.max_stop_distance
        ):
            raise ValueError(
                f"min_stop_distance ({self.min_stop_distance}) cannot exceed "
                f"max_stop_distance ({self.max_stop_distance})"
            )

        if self.min_stop_distance is not None and self.min_stop_distance < 0:
            raise ValueError(
                f"min_stop_distance must be non-negative, got {self.min_stop_distance}"
            )

        if self.max_stop_distance is not None and self.max_stop_distance < 0:
            raise ValueError(
                f"max_stop_distance must be non-negative, got {self.max_stop_distance}"
            )

        return True
