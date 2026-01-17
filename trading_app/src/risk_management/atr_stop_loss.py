"""
ATR (Average True Range) based stop loss strategy implementation.
"""

from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import pandas as pd

from src.risk_management.stop_loss_strategy import StopLossStrategy

logger = logging.getLogger(__name__)


@dataclass
class ATRStopLoss(StopLossStrategy):
    """
    ATR-based stop loss strategy.

    Calculates stop loss based on the Average True Range (ATR) of the stock.
    ATR measures volatility, making this strategy adaptive to market conditions.

    Example:
        # 2x ATR stop with 3:1 reward:risk
        from connectors.twelve_data import TwelveDataConnector
        connector = TwelveDataConnector(api_key="xxx")

        strategy = ATRStopLoss(
            atr_multiplier=2.0,
            atr_period=14,
            data_connector=connector,
            reward_risk_ratio=3.0
        )

        entry = 100.0
        stop = strategy.calculate_stop_price(entry, "TQQQ")  # e.g., 94.0 if ATR=3.0
        target = strategy.calculate_take_profit_price(entry, "TQQQ")  # e.g., 118.0

    Attributes:
        atr_multiplier: Multiplier for ATR (e.g., 2.0 means 2x ATR)
        atr_period: Period for ATR calculation (default 14)
        data_connector: Instance of TwelveDataConnector to fetch historical data
        reward_risk_ratio: Optional reward:risk ratio for take profit (e.g., 3.0 = 3:1)
        cache_duration_minutes: How long to cache ATR values (default 30)
        fallback_percentage: Fallback stop percentage if ATR calculation fails (default 0.05)
    """

    atr_multiplier: float
    atr_period: int
    data_connector: object  # TwelveDataConnector instance
    reward_risk_ratio: Optional[float] = None
    cache_duration_minutes: int = 30
    fallback_percentage: float = 0.05
    _atr_cache: Dict[str, Tuple[float, datetime]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()

    def _calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range for each period.

        True Range is the maximum of:
        - High - Low
        - |High - Previous Close|
        - |Low - Previous Close|

        Args:
            df: DataFrame with High, Low, Close columns

        Returns:
            Series with True Range values
        """
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift(1)).abs()
        low_close = (df['Low'] - df['Close'].shift(1)).abs()

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range

    def _calculate_atr(self, df: pd.DataFrame) -> Optional[float]:
        """
        Calculate Average True Range.

        Args:
            df: DataFrame with OHLC data

        Returns:
            ATR value or None if insufficient data
        """
        if len(df) < self.atr_period + 1:
            logger.warning(
                f"Insufficient data for ATR calculation: need {self.atr_period + 1}, "
                f"got {len(df)}"
            )
            return None

        true_range = self._calculate_true_range(df)
        atr = true_range.rolling(window=self.atr_period).mean()

        # Get the latest ATR value (skip NaN values from rolling calculation)
        latest_atr = atr.iloc[-1]

        if pd.isna(latest_atr):
            logger.warning("ATR calculation resulted in NaN")
            return None

        return float(latest_atr)

    def _get_cached_atr(self, symbol: str) -> Optional[float]:
        """
        Get cached ATR value if available and not expired.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Cached ATR value or None if not available/expired
        """
        if symbol not in self._atr_cache:
            return None

        atr_value, timestamp = self._atr_cache[symbol]
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60

        if age_minutes > self.cache_duration_minutes:
            logger.info(f"{symbol}: ATR cache expired ({age_minutes:.1f} min old)")
            del self._atr_cache[symbol]
            return None

        logger.info(f"{symbol}: Using cached ATR {atr_value:.4f} ({age_minutes:.1f} min old)")
        return atr_value

    def _cache_atr(self, symbol: str, atr_value: float):
        """
        Cache ATR value with timestamp.

        Args:
            symbol: Stock ticker symbol
            atr_value: ATR value to cache
        """
        self._atr_cache[symbol] = (atr_value, datetime.now())
        logger.info(f"{symbol}: Cached ATR {atr_value:.4f}")

    def _fetch_atr(self, symbol: str) -> Optional[float]:
        """
        Fetch historical data and calculate ATR.

        Args:
            symbol: Stock ticker symbol

        Returns:
            ATR value or None if calculation fails
        """
        try:
            # Check cache first
            cached_atr = self._get_cached_atr(symbol)
            if cached_atr is not None:
                return cached_atr

            # Fetch hourly data (need atr_period + 1 for previous close calculation)
            required_bars = self.atr_period + 5  # Add buffer for market gaps
            logger.info(
                f"{symbol}: Fetching {required_bars} hourly bars for {self.atr_period}-period ATR"
            )

            df = self.data_connector.get_stock_data(
                symbol=symbol,
                interval="1h",
                outputsize=required_bars
            )

            if df is None or df.empty:
                logger.error(f"{symbol}: Failed to fetch historical data for ATR")
                return None

            # Calculate ATR
            atr = self._calculate_atr(df)

            if atr is not None:
                # Cache the result
                self._cache_atr(symbol, atr)
                logger.info(f"{symbol}: Calculated ATR: {atr:.4f} ({self.atr_period}-period)")

            return atr

        except Exception as e:
            logger.error(f"{symbol}: Error calculating ATR: {str(e)}")
            return None

    def calculate_stop_price(self, entry_price: float, symbol: str) -> float:
        """
        Calculate the stop loss price based on ATR.

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

        # Fetch ATR
        atr = self._fetch_atr(symbol)

        if atr is None:
            # Fallback to percentage-based stop
            logger.warning(
                f"{symbol}: ATR calculation failed, using fallback "
                f"{self.fallback_percentage * 100:.1f}% stop"
            )
            stop_distance = entry_price * self.fallback_percentage
        else:
            # Calculate stop distance using ATR
            stop_distance = self.atr_multiplier * atr

        stop_price = entry_price - stop_distance

        logger.info(
            f"{symbol}: Calculated stop price ${stop_price:.2f} "
            f"(${stop_distance:.2f} below entry ${entry_price:.2f})"
        )

        return round(stop_price, 2)

    def calculate_take_profit_price(self, entry_price: float, symbol: str) -> Optional[float]:
        """
        Calculate the take profit price based on reward:risk ratio.

        Args:
            entry_price: The entry price of the position
            symbol: The stock ticker symbol

        Returns:
            The calculated take profit price, or None if not configured
        """
        if self.reward_risk_ratio is None:
            return None

        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")

        # Calculate stop price to get risk amount
        stop_price = self.calculate_stop_price(entry_price, symbol)
        risk_amount = entry_price - stop_price

        # Calculate target based on reward:risk ratio
        target_price = entry_price + (risk_amount * self.reward_risk_ratio)

        logger.info(
            f"{symbol}: Calculated take profit ${target_price:.2f} "
            f"({self.reward_risk_ratio}:1 R:R, risk ${risk_amount:.2f})"
        )

        return round(target_price, 2)

    def get_strategy_name(self) -> str:
        """
        Get a descriptive name for this strategy.

        Returns:
            Strategy name with ATR parameters
        """
        name = f"ATR-Based ({self.atr_multiplier}x, {self.atr_period}-period)"
        if self.reward_risk_ratio is not None:
            name += f" [R:R {self.reward_risk_ratio}:1]"
        return name

    def validate(self) -> bool:
        """
        Validate strategy parameters.

        Returns:
            True if valid

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate ATR multiplier
        if not 0.5 <= self.atr_multiplier <= 5.0:
            raise ValueError(
                f"atr_multiplier must be between 0.5 and 5.0, got {self.atr_multiplier}"
            )

        # Validate ATR period
        if not 5 <= self.atr_period <= 50:
            raise ValueError(
                f"atr_period must be between 5 and 50, got {self.atr_period}"
            )

        # Validate reward:risk ratio if specified
        if self.reward_risk_ratio is not None and self.reward_risk_ratio <= 0:
            raise ValueError(
                f"reward_risk_ratio must be positive, got {self.reward_risk_ratio}"
            )

        # Validate cache duration
        if self.cache_duration_minutes < 0:
            raise ValueError(
                f"cache_duration_minutes must be non-negative, got {self.cache_duration_minutes}"
            )

        # Validate fallback percentage
        if not 0.001 <= self.fallback_percentage <= 0.5:
            raise ValueError(
                f"fallback_percentage must be between 0.001 and 0.5, got {self.fallback_percentage}"
            )

        # Validate data connector
        if self.data_connector is None:
            raise ValueError("data_connector cannot be None")

        return True
