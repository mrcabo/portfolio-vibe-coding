import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

def get_stock_data_yahoo(ticker, period="1mo"):
    """Get stock data from Yahoo Finance API
    
    Args:
        ticker: Stock symbol
        period: One of: 1d, 1w, 1mo, 3mo, 6mo, 1y
    
    Returns:
        StockData object with info and history
    """
    print(f"Fetching data for {ticker} from Yahoo Finance...")
    
    try:
        # Convert period to yfinance format
        yf_period_map = {
            "1d": "1d",
            "1w": "5d",
            "1mo": "1mo",
            "3mo": "3mo",
            "6mo": "6mo",
            "1y": "1y"
        }
        
        yf_period = yf_period_map.get(period, "1mo")
        
        # Get stock data from yfinance
        stock = yf.Ticker(ticker)
        
        # Get quote data
        info = stock.info
        
        if not info:
            print(f"Could not get info for {ticker}")
            return None
        
        # Create a simpler quote structure similar to the previous API
        quote = {
            "symbol": ticker,
            "price": info.get("regularMarketPrice", 0),
            "change": info.get("regularMarketChange", 0),
            "change_percent": info.get("regularMarketChangePercent", 0)
        }
        
        # Get historical data with appropriate interval based on period
        interval = "1d"  # Default interval
        if period == "1d":
            interval = "5m"  # 5-minute intervals for 1-day view
        elif period == "1w":
            interval = "30m"  # 30-minute intervals for 1-week view
            
        hist = stock.history(period=yf_period, interval=interval)
        
        # If we don't have any history data, get at least 2 days of daily data
        if hist is None or hist.empty:
            print(f"No historical data for {ticker}, retrieving minimal data...")
            hist = stock.history(period="2d")
        
        # Add the current price to the history if it's not already there
        if not hist.empty and quote["price"] > 0:
            current_time = pd.Timestamp.now()
            if current_time not in hist.index:
                # Create a new row with current price
                new_data = pd.DataFrame({
                    'Open': [quote["price"]],
                    'High': [quote["price"]],
                    'Low': [quote["price"]],
                    'Close': [quote["price"]],
                    'Volume': [0]
                }, index=[current_time])
                
                hist = pd.concat([new_data, hist])
        
        # Create a class similar to the previous API's StockData
        class StockData:
            def __init__(self, ticker, quote, hist, info):
                self.ticker = ticker
                self.info = {
                    "regularMarketPrice": quote["price"],
                    "shortName": info.get("shortName", ticker),
                    "changePercent": quote["change_percent"]
                }
                self._hist = hist
                
            def history(self, period=None):
                return self._hist
        
        return StockData(ticker, quote, hist, info)
        
    except Exception as e:
        print(f"Error fetching data for {ticker}: {str(e)}")
        return None