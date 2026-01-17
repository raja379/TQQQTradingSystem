"""
Main Trading Lambda handler for orchestrating trading operations.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from signals.twelve_data_ema import TwelveDataEMASignal
from trading.alpaca_trader import AlpacaTrader
from risk_management.percentage_stop_loss import PercentageStopLoss
from risk_management.atr_stop_loss import ATRStopLoss
from connectors.twelve_data import TwelveDataConnector

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _create_stop_loss_strategy():
    """
    Create stop loss strategy based on environment variables.

    Environment variables:
        STOP_LOSS_STRATEGY: "percentage", "atr", or "none" (default: "none")
        STOP_LOSS_PERCENTAGE: Stop loss percentage (default: 0.05 = 5%)
        TAKE_PROFIT_PERCENTAGE: Take profit percentage (default: None)
        ATR_MULTIPLIER: ATR multiplier for ATR strategy (default: 2.0)
        ATR_PERIOD: ATR period for ATR strategy (default: 14)
        REWARD_RISK_RATIO: Reward:risk ratio for take profit (default: None)

    Returns:
        StopLossStrategy instance or None
    """
    strategy_type = os.environ.get('STOP_LOSS_STRATEGY', 'none').lower()

    if strategy_type == 'none':
        logger.info("No stop loss strategy configured")
        return None

    elif strategy_type == 'percentage':
        stop_loss_pct = float(os.environ.get('STOP_LOSS_PERCENTAGE', '0.05'))
        take_profit_pct_str = os.environ.get('TAKE_PROFIT_PERCENTAGE')
        take_profit_pct = float(take_profit_pct_str) if take_profit_pct_str else None

        strategy = PercentageStopLoss(
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )

        logger.info(f"Configured {strategy.get_strategy_name()}")
        return strategy

    elif strategy_type == 'atr':
        atr_multiplier = float(os.environ.get('ATR_MULTIPLIER', '2.0'))
        atr_period = int(os.environ.get('ATR_PERIOD', '14'))
        reward_risk_str = os.environ.get('REWARD_RISK_RATIO')
        reward_risk_ratio = float(reward_risk_str) if reward_risk_str else None

        # Create data connector for ATR calculation
        data_connector = TwelveDataConnector()

        strategy = ATRStopLoss(
            atr_multiplier=atr_multiplier,
            atr_period=atr_period,
            data_connector=data_connector,
            reward_risk_ratio=reward_risk_ratio
        )

        logger.info(f"Configured {strategy.get_strategy_name()}")
        return strategy

    else:
        logger.warning(f"Unknown stop loss strategy: {strategy_type}, using none")
        return None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main trading Lambda handler triggered by EventBridge cron.

    Args:
        event: Lambda event data from EventBridge
        context: Lambda context

    Returns:
        Dict containing trading execution results
    """
    try:
        current_time = datetime.now().isoformat()
        logger.info(f"Trading Lambda triggered at {current_time}")
        logger.info(f"Event: {json.dumps(event)}")

        # Initialize stop loss strategy
        stop_loss_strategy = _create_stop_loss_strategy()

        # Initialize Twelve Data EMA signal analyzer
        signal_analyzer = TwelveDataEMASignal()

        # Define watchlist - simplified to focus on TQQQ only
        watchlist = ['TQQQ']

        # Get market signals using Twelve Data
        logger.info(f"Analyzing market signals for watchlist: {watchlist}")
        trading_signals = signal_analyzer.analyze_multiple(watchlist)

        # Execute trades via Alpaca with stop loss strategy
        logger.info("Executing TQQQ-focused strategy via Alpaca")
        alpaca_trader = AlpacaTrader(paper_trading=True, stop_loss_strategy=stop_loss_strategy)
        trading_results = alpaca_trader.process_all_stocks(trading_signals)
        
        # Count signals
        signal_summary = {
            "bullish": sum(1 for s in trading_signals.values() 
                          if s and s.get("signal") == "bullish"),
            "bearish": sum(1 for s in trading_signals.values() 
                          if s and s.get("signal") == "bearish"),
            "neutral": sum(1 for s in trading_signals.values() 
                          if s and s.get("signal") == "neutral"),
            "no_data": sum(1 for s in trading_signals.values() 
                          if s and s.get("status") in ["no_data", "error"])
        }
        
        result = {
            "message": "Trading execution completed",
            "timestamp": current_time,
            "watchlist": watchlist,
            "signal_summary": signal_summary,
            "detailed_signals": trading_signals,
            "trading_results": trading_results,
            "event_received": event
        }
        
        logger.info(f"Trading execution complete. Signals: {signal_summary}, Orders: {trading_results.get('total_orders', 0)}")
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in main trading handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"Trading analysis failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        }