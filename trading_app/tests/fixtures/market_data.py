"""
Test fixtures for market data.
"""

import pandas as pd
from datetime import datetime, timedelta


def create_sample_ohlcv_data(symbol='TQQQ', days=30, start_price=100.0, trend='sideways'):
    """
    Create sample OHLCV data for testing.
    
    Args:
        symbol: Stock symbol
        days: Number of days of data
        start_price: Starting price
        trend: 'up', 'down', or 'sideways'
    
    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='H')
    
    prices = []
    current_price = start_price
    
    for i in range(days):
        if trend == 'up':
            change = 0.02 + (i % 5) * 0.01
        elif trend == 'down':
            change = -0.02 - (i % 5) * 0.01
        else:  # sideways
            change = ((i % 7) - 3) * 0.005
        
        current_price *= (1 + change)
        prices.append(current_price)
    
    # Create OHLCV data
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        high = price * 1.02
        low = price * 0.98
        open_price = price * 0.999
        volume = 1000000 + (i % 10) * 100000
        
        data.append({
            'Date': date,
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': price,
            'Volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('Date', inplace=True)
    return df


def create_bullish_scenario():
    """Create market data for bullish EMA scenario."""
    return create_sample_ohlcv_data(trend='up', start_price=100.0)


def create_bearish_scenario():
    """Create market data for bearish EMA scenario."""
    return create_sample_ohlcv_data(trend='down', start_price=110.0)


def create_neutral_scenario():
    """Create market data for neutral EMA scenario."""
    return create_sample_ohlcv_data(trend='sideways', start_price=105.0)


def create_twelve_data_response(ohlcv_data):
    """
    Create Twelve Data API response format from OHLCV data.
    
    Args:
        ohlcv_data: DataFrame with OHLCV data
    
    Returns:
        Dict in Twelve Data format
    """
    values = []
    for date, row in ohlcv_data.iterrows():
        values.append({
            'datetime': date.strftime('%Y-%m-%d %H:%M:%S'),
            'open': str(row['Open']),
            'high': str(row['High']),
            'low': str(row['Low']),
            'close': str(row['Close']),
            'volume': str(int(row['Volume']))
        })
    
    # Reverse to match API format (newest first)
    values.reverse()
    
    return {
        'meta': {
            'symbol': 'TQQQ',
            'interval': '1h',
            'currency': 'USD',
            'exchange_timezone': 'America/New_York'
        },
        'values': values,
        'status': 'ok'
    }