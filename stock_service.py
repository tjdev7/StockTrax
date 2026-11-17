import asyncio
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional
from cachetools import TTLCache

# Cache with TTL of 30 seconds, max 200 items
price_cache = TTLCache(maxsize=200, ttl=30)

async def get_stock_price(symbol: str, force_refresh: bool = False) -> Optional[float]:
    """
    Get current price for a symbol.
    Uses cache unless force_refresh=True.
    Returns None if price cannot be fetched.
    """
    symbol = symbol.upper()
    if not force_refresh and symbol in price_cache:
        return price_cache[symbol]

    # yfinance is synchronous; run in thread pool
    loop = asyncio.get_event_loop()
    try:
        ticker = await loop.run_in_executor(None, lambda: yf.Ticker(symbol))
        # Try to get current price: prefer 'regularMarketPrice', fallback to 'currentPrice'
        info = await loop.run_in_executor(None, lambda: ticker.info)
        price = info.get('regularMarketPrice') or info.get('currentPrice')
        if price is None:
            # Fallback: fetch historical data for last 1 day
            hist = await loop.run_in_executor(
                None, lambda: ticker.history(period='1d', interval='1m')
            )
            if not hist.empty:
                price = hist['Close'].iloc[-1]
        if price is not None:
            price_cache[symbol] = price
            return price
    except Exception as e:
        # Log error (we'll print for demo, use proper logging in production)
        print(f"Error fetching {symbol}: {e}")
    return None