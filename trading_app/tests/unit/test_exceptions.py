"""
Unit tests for custom exceptions.
"""

import pytest
from src.exceptions import (
    TradingSystemError,
    DataFetchError,
    CalculationError,
    TradeExecutionError,
    ConfigurationError
)


class TestTradingSystemError:
    """Test cases for TradingSystemError base exception."""

    def test_raise_trading_system_error(self):
        """Test raising TradingSystemError."""
        with pytest.raises(TradingSystemError) as exc_info:
            raise TradingSystemError("Base trading error")

        assert str(exc_info.value) == "Base trading error"

    def test_trading_system_error_inheritance(self):
        """Test TradingSystemError inherits from Exception."""
        error = TradingSystemError("test")
        assert isinstance(error, Exception)

    def test_trading_system_error_empty_message(self):
        """Test TradingSystemError with empty message."""
        error = TradingSystemError()
        assert str(error) == ""


class TestDataFetchError:
    """Test cases for DataFetchError exception."""

    def test_raise_data_fetch_error(self):
        """Test raising DataFetchError."""
        with pytest.raises(DataFetchError) as exc_info:
            raise DataFetchError("Failed to fetch market data")

        assert str(exc_info.value) == "Failed to fetch market data"

    def test_data_fetch_error_inheritance(self):
        """Test DataFetchError inherits from TradingSystemError."""
        error = DataFetchError("test")
        assert isinstance(error, TradingSystemError)
        assert isinstance(error, Exception)

    def test_catch_data_fetch_as_trading_system_error(self):
        """Test catching DataFetchError as TradingSystemError."""
        with pytest.raises(TradingSystemError):
            raise DataFetchError("API timeout")


class TestCalculationError:
    """Test cases for CalculationError exception."""

    def test_raise_calculation_error(self):
        """Test raising CalculationError."""
        with pytest.raises(CalculationError) as exc_info:
            raise CalculationError("EMA calculation failed")

        assert str(exc_info.value) == "EMA calculation failed"

    def test_calculation_error_inheritance(self):
        """Test CalculationError inherits from TradingSystemError."""
        error = CalculationError("test")
        assert isinstance(error, TradingSystemError)
        assert isinstance(error, Exception)

    def test_catch_calculation_as_trading_system_error(self):
        """Test catching CalculationError as TradingSystemError."""
        with pytest.raises(TradingSystemError):
            raise CalculationError("Division by zero")


class TestTradeExecutionError:
    """Test cases for TradeExecutionError exception."""

    def test_raise_trade_execution_error(self):
        """Test raising TradeExecutionError."""
        with pytest.raises(TradeExecutionError) as exc_info:
            raise TradeExecutionError("Order rejected by broker")

        assert str(exc_info.value) == "Order rejected by broker"

    def test_trade_execution_error_inheritance(self):
        """Test TradeExecutionError inherits from TradingSystemError."""
        error = TradeExecutionError("test")
        assert isinstance(error, TradingSystemError)
        assert isinstance(error, Exception)

    def test_catch_trade_execution_as_trading_system_error(self):
        """Test catching TradeExecutionError as TradingSystemError."""
        with pytest.raises(TradingSystemError):
            raise TradeExecutionError("Insufficient buying power")


class TestConfigurationError:
    """Test cases for ConfigurationError exception."""

    def test_raise_configuration_error(self):
        """Test raising ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Missing API key")

        assert str(exc_info.value) == "Missing API key"

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from TradingSystemError."""
        error = ConfigurationError("test")
        assert isinstance(error, TradingSystemError)
        assert isinstance(error, Exception)

    def test_catch_configuration_as_trading_system_error(self):
        """Test catching ConfigurationError as TradingSystemError."""
        with pytest.raises(TradingSystemError):
            raise ConfigurationError("Invalid configuration")


class TestExceptionHierarchy:
    """Test the overall exception hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test all custom exceptions inherit from TradingSystemError."""
        exceptions = [
            DataFetchError("test"),
            CalculationError("test"),
            TradeExecutionError("test"),
            ConfigurationError("test")
        ]

        for exc in exceptions:
            assert isinstance(exc, TradingSystemError)

    def test_catching_all_custom_exceptions(self):
        """Test catching all custom exceptions with base class."""
        errors_to_raise = [
            DataFetchError("data error"),
            CalculationError("calc error"),
            TradeExecutionError("trade error"),
            ConfigurationError("config error")
        ]

        caught_count = 0
        for error in errors_to_raise:
            try:
                raise error
            except TradingSystemError:
                caught_count += 1

        assert caught_count == 4

    def test_exception_with_complex_message(self):
        """Test exceptions with complex error messages."""
        error_msg = "Failed to execute order: symbol=TQQQ, qty=100, reason=insufficient_funds"
        error = TradeExecutionError(error_msg)

        assert "symbol=TQQQ" in str(error)
        assert "qty=100" in str(error)
        assert "insufficient_funds" in str(error)
