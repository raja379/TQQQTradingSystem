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

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        
        # Initialize Twelve Data EMA signal analyzer
        signal_analyzer = TwelveDataEMASignal()
        
        # Define watchlist - simplified to focus on TQQQ only
        watchlist = ['TQQQ']
        
        # Get market signals using Twelve Data
        logger.info(f"Analyzing market signals for watchlist: {watchlist}")
        trading_signals = signal_analyzer.analyze_multiple(watchlist)
        
        # Execute trades via Alpaca
        logger.info("Executing TQQQ-focused strategy via Alpaca")
        alpaca_trader = AlpacaTrader(paper_trading=True)
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