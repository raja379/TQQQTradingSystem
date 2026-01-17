# Stop Loss Strategy Pattern Implementation

This document describes the flexible stop loss strategy system implemented for the TQQQ automated trading system using the Strategy design pattern.

## Overview

The stop loss system allows you to choose between different risk management strategies that automatically calculate stop loss and take profit levels for your trades. The system is designed to be:

- **Flexible**: Easily switch between different stop loss strategies
- **Extensible**: Add new strategies without modifying existing code
- **Backward Compatible**: Works seamlessly with existing code (strategies are optional)
- **Well-Tested**: Comprehensive unit and integration tests (61 tests passing)

## Architecture

### Strategy Pattern

The implementation uses the Strategy pattern with:

1. **StopLossStrategy** (abstract base class): Defines the interface for all strategies
2. **PercentageStopLoss**: Fixed percentage-based stop loss
3. **ATRStopLoss**: Adaptive stop loss based on Average True Range (ATR)
4. **AlpacaTrader**: Trading client that uses the strategies

### File Structure

```
trading_app/
├── src/
│   ├── risk_management/
│   │   ├── __init__.py
│   │   ├── stop_loss_strategy.py      # Abstract base class
│   │   ├── percentage_stop_loss.py    # Percentage-based strategy
│   │   └── atr_stop_loss.py           # ATR-based strategy
│   └── trading/
│       └── alpaca_trader.py           # Modified to support strategies
├── tests/
│   ├── unit/
│   │   └── risk_management/
│   │       ├── test_percentage_stop_loss.py  # 24 tests
│   │       └── test_atr_stop_loss.py         # 25 tests
│   └── integration/
│       └── test_stop_loss_integration.py     # 12 tests
└── main.py                             # Updated with configuration
```

## Usage Examples

### Example 1: Percentage-Based Stop Loss

```python
from risk_management.percentage_stop_loss import PercentageStopLoss
from trading.alpaca_trader import AlpacaTrader

# 5% stop loss, 15% take profit (3:1 reward:risk)
stop_loss_strategy = PercentageStopLoss(
    stop_loss_pct=0.05,
    take_profit_pct=0.15
)

trader = AlpacaTrader(
    paper_trading=True,
    stop_loss_strategy=stop_loss_strategy
)

# When buying TQQQ at $100:
# - Entry: $100
# - Stop: $95 (5% below entry)
# - Target: $115 (15% above entry, 3:1 R:R)
```

### Example 2: ATR-Based Stop Loss

```python
from risk_management.atr_stop_loss import ATRStopLoss
from connectors.twelve_data import TwelveDataConnector

data_connector = TwelveDataConnector(api_key="your_api_key")

# 2x ATR stop with 3:1 reward:risk
stop_loss_strategy = ATRStopLoss(
    atr_multiplier=2.0,
    atr_period=14,
    data_connector=data_connector,
    reward_risk_ratio=3.0
)

trader = AlpacaTrader(
    paper_trading=True,
    stop_loss_strategy=stop_loss_strategy
)

# When buying TQQQ at $100:
# - Fetches 14-period hourly ATR (e.g., ATR = $3.00)
# - Entry: $100
# - Stop: $94 (2 * $3 below entry = $6 stop distance)
# - Target: $118 (3:1 R:R = $18 target distance)
```

### Example 3: No Stop Loss (Backward Compatible)

```python
from trading.alpaca_trader import AlpacaTrader

# No stop loss strategy - works exactly as before
trader = AlpacaTrader(paper_trading=True)
```

### Example 4: Changing Strategy at Runtime

```python
trader = AlpacaTrader(paper_trading=True)

# Start with percentage strategy
trader.set_stop_loss_strategy(PercentageStopLoss(stop_loss_pct=0.05))

# Change to ATR strategy
trader.set_stop_loss_strategy(ATRStopLoss(
    atr_multiplier=2.0,
    atr_period=14,
    data_connector=connector
))

# Disable stop loss
trader.set_stop_loss_strategy(None)
```

## Configuration via Environment Variables

The system can be configured using environment variables in `main.py`:

### Percentage-Based Strategy

```bash
export STOP_LOSS_STRATEGY="percentage"
export STOP_LOSS_PERCENTAGE="0.05"        # 5% stop loss
export TAKE_PROFIT_PERCENTAGE="0.15"      # 15% take profit (optional)
```

### ATR-Based Strategy

```bash
export STOP_LOSS_STRATEGY="atr"
export ATR_MULTIPLIER="2.0"               # 2x ATR
export ATR_PERIOD="14"                    # 14-period ATR
export REWARD_RISK_RATIO="3.0"            # 3:1 R:R (optional)
```

### No Stop Loss (Default)

```bash
export STOP_LOSS_STRATEGY="none"          # Or omit the variable
```

## Strategy Details

### PercentageStopLoss

**Parameters:**
- `stop_loss_pct` (required): Percentage below entry for stop (0.001 to 0.5)
- `take_profit_pct` (optional): Percentage above entry for profit target
- `min_stop_distance` (optional): Minimum dollar distance for stop
- `max_stop_distance` (optional): Maximum dollar distance for stop

**Features:**
- Simple and predictable
- Same percentage regardless of volatility
- Optional min/max constraints for risk control
- Automatic reward:risk ratio calculation

**Best For:**
- Consistent risk per trade
- Low volatility instruments
- Traders who prefer fixed percentages

### ATRStopLoss

**Parameters:**
- `atr_multiplier` (required): Multiplier for ATR (0.5 to 5.0)
- `atr_period` (required): Period for ATR calculation (5 to 50)
- `data_connector` (required): TwelveDataConnector instance
- `reward_risk_ratio` (optional): Reward:risk ratio for take profit
- `cache_duration_minutes` (optional): ATR cache duration (default: 30)
- `fallback_percentage` (optional): Fallback if ATR fails (default: 0.05)

**Features:**
- Adaptive to market volatility
- Wider stops in volatile markets, tighter in calm markets
- Automatic ATR caching (30 min default)
- Fallback to percentage if data fetch fails
- Uses hourly bars for calculation

**Best For:**
- Volatile instruments (like TQQQ)
- Adaptive risk management
- Following market conditions

## Alpaca Bracket Orders

When a stop loss strategy is configured, the system automatically creates **bracket orders** with Alpaca:

```json
{
  "symbol": "TQQQ",
  "qty": "100",
  "side": "buy",
  "type": "market",
  "time_in_force": "day",
  "order_class": "bracket",
  "stop_loss": {
    "stop_price": "95.00"
  },
  "take_profit": {
    "limit_price": "115.00"
  }
}
```

### Bracket Order Benefits

- **Automatic Risk Management**: Stop loss and take profit orders placed simultaneously
- **No Manual Intervention**: Orders execute automatically at target levels
- **Risk Defined Upfront**: Know your risk before entering the trade
- **Profit Protection**: Take profit locks in gains automatically

## Testing

The implementation includes comprehensive tests:

### Unit Tests (49 tests)

**PercentageStopLoss** (24 tests):
- Parameter validation
- Stop/target calculation at various percentages
- Min/max distance enforcement
- Edge cases and error handling

**ATRStopLoss** (25 tests):
- True Range and ATR calculation
- Cache mechanism
- Fallback behavior
- Different multipliers
- Realistic TQQQ scenarios

### Integration Tests (12 tests)

- Integration with AlpacaTrader
- Bracket order placement
- Strategy switching
- Backward compatibility
- Error handling and fallbacks

**Run tests:**
```bash
# All risk management tests
pytest tests/unit/risk_management/ tests/integration/test_stop_loss_integration.py -v

# Specific strategy
pytest tests/unit/risk_management/test_percentage_stop_loss.py -v
pytest tests/unit/risk_management/test_atr_stop_loss.py -v
```

## Implementation Details

### AlpacaTrader Modifications

**New Constructor Parameter:**
```python
def __init__(self, paper_trading: bool = True,
             stop_loss_strategy: Optional[StopLossStrategy] = None):
```

**New Method:**
```python
def set_stop_loss_strategy(self, strategy: Optional[StopLossStrategy]) -> None:
```

**Updated Methods:**
- `place_buy_order()`: Added `use_stop_loss` parameter, creates bracket orders
- `buy_tqqq_with_all_funds()`: Uses stop loss strategy if configured
- `process_all_stocks()`: Includes strategy info in results

**Updated AlpacaOrder:**
```python
@dataclass
class AlpacaOrder:
    ...
    stop_price: Optional[float] = None
    take_profit_price: Optional[float] = None
```

### ATR Calculation

The ATR strategy calculates Average True Range as follows:

1. **True Range (TR)** = max of:
   - High - Low
   - |High - Previous Close|
   - |Low - Previous Close|

2. **ATR** = Simple Moving Average of TR over the period

3. **Stop Distance** = ATR × Multiplier

4. **Stop Price** = Entry Price - Stop Distance

### Caching Mechanism

ATRStopLoss caches ATR values to avoid redundant API calls:

- Default cache duration: 30 minutes
- Stores: `{symbol: (atr_value, timestamp)}`
- Automatically invalidates after expiration
- Reduces API calls for repeated calculations

## Error Handling

The system includes robust error handling:

1. **Validation**: All parameters validated at initialization
2. **Fallback**: ATR strategy falls back to percentage if data fetch fails
3. **Graceful Degradation**: Orders still placed if stop loss calculation fails
4. **Logging**: Comprehensive logging for debugging
5. **Backward Compatibility**: System works without strategy

## Best Practices

### Choosing a Strategy

**Use Percentage-Based when:**
- You want consistent risk per trade
- Trading less volatile instruments
- You prefer simplicity and predictability
- You're starting out with systematic trading

**Use ATR-Based when:**
- Trading volatile instruments (like TQQQ)
- You want adaptive risk management
- Market conditions change frequently
- You prefer volatility-adjusted stops

### Parameter Selection

**Percentage-Based:**
- **Stop Loss**: 3-5% for TQQQ, 2-3% for less volatile
- **Reward:Risk**: Minimum 2:1, prefer 3:1 or higher
- Use min_stop_distance to avoid stops too close to entry

**ATR-Based:**
- **Multiplier**: Start with 2.0, adjust based on testing
- **Period**: 14 is standard, use 10 for faster adaptation
- **Reward:Risk**: 2:1 to 3:1 is typical
- Test with different multipliers (1.5x, 2.0x, 2.5x)

### Risk Management Tips

1. **Position Sizing**: Adjust quantity based on stop distance
2. **Maximum Risk**: Never risk more than 1-2% of account per trade
3. **Reward:Risk**: Aim for minimum 2:1, preferably 3:1
4. **Testing**: Backtest strategies before live trading
5. **Monitoring**: Log and review stop loss effectiveness

## Future Enhancements

Potential additions to the stop loss system:

1. **Time-Based Stops**: Exit after X hours/days
2. **Trailing Stops**: Move stop up as price moves in your favor
3. **Technical Level Stops**: Use support/resistance levels
4. **Volatility Breakout Stops**: Based on Bollinger Bands
5. **Multiple Stop Levels**: Partial exits at different levels
6. **Dynamic Position Sizing**: Calculate position size based on stop distance

## Troubleshooting

### Common Issues

**Issue**: ATR calculation fails
- **Solution**: Check data connector API key, verify sufficient historical data
- **Fallback**: System automatically uses fallback_percentage

**Issue**: Bracket order rejected
- **Solution**: Check if symbol supports bracket orders, verify stop/target prices

**Issue**: Stop too tight or too wide
- **Solution**: Adjust percentage or ATR multiplier, consider min/max constraints

### Logs to Check

```python
# Strategy initialization
INFO: Initialized with stop loss strategy: Percentage-Based (5.0%) [R:R 3.0:1]

# Bracket order
INFO: TQQQ: Bracket order - Entry $100.00, Stop $95.00, Target $115.00

# ATR calculation
INFO: TQQQ: Calculated ATR: 3.5000 (14-period)
INFO: TQQQ: Using cached ATR 3.5000 (15.2 min old)

# Fallback
WARNING: TQQQ: ATR calculation failed, using fallback 5.0% stop
```

## Summary

The stop loss strategy system provides:

- ✅ Flexible strategy selection
- ✅ Two production-ready strategies (Percentage, ATR)
- ✅ Easy to extend with new strategies
- ✅ Backward compatible with existing code
- ✅ Comprehensive test coverage (61 tests)
- ✅ Environment variable configuration
- ✅ Automatic bracket order creation
- ✅ Robust error handling with fallbacks
- ✅ Detailed logging for debugging
- ✅ Production-ready implementation

The implementation follows SOLID principles and provides a clean, maintainable foundation for risk management in automated trading systems.
