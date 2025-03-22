import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import random
import json

class AlphaVantageAPI:
    """Class to handle Alpha Vantage API calls with better error handling"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        # Custom headers to make requests look more like a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    
    def get_quote(self, symbol):
        """Get current stock quote"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        print(f"Requesting quote for {symbol}...")
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers)
            data = response.json()
            
            # Check for error messages
            if "Error Message" in data:
                print(f"API error: {data['Error Message']}")
                return None
                
            if "Note" in data:
                print(f"API limit message: {data['Note']}")
                # Sleep if we hit rate limit
                time.sleep(12)  # Wait for rate limit to reset
                return None
            
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                
                # Check if we got a valid quote
                if "05. price" not in quote or not quote["05. price"]:
                    print(f"No price data for {symbol}")
                    return None
                
                return {
                    "symbol": quote.get("01. symbol", symbol),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": float(quote.get("10. change percent", "0").strip("%"))
                }
            
            # If we get here, we didn't get a valid response
            print(f"Unexpected response for {symbol}: {json.dumps(data)[:200]}...")
            return None
            
        except Exception as e:
            print(f"Error getting quote for {symbol}: {str(e)}")
            return None
    
    def get_daily_adjusted(self, symbol, period="1mo"):
        """Get historical price data"""
        # Map period to outputsize
        outputsize = "compact"  # Default to last 100 data points
        if period in ["6mo", "1y"]:
            outputsize = "full"  # Get up to 20 years of data
            
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self.api_key
        }
        
        print(f"Requesting daily adjusted data for {symbol}...")
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers)
            data = response.json()
            
            # Check for error messages
            if "Error Message" in data:
                print(f"API error: {data['Error Message']}")
                return None
                
            if "Note" in data:
                print(f"API limit message: {data['Note']}")
                # Sleep if we hit rate limit
                time.sleep(12)  # Wait for rate limit to reset
                return None
            
            if "Time Series (Daily)" in data:
                # Convert to DataFrame
                df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
                
                # Rename columns
                df = df.rename(columns={
                    "1. open": "Open",
                    "2. high": "High",
                    "3. low": "Low", 
                    "4. close": "Close",
                    "5. adjusted close": "Adjusted Close",
                    "6. volume": "Volume"
                })
                
                # Convert data types
                for col in ["Open", "High", "Low", "Close", "Adjusted Close"]:
                    df[col] = pd.to_numeric(df[col])
                df["Volume"] = pd.to_numeric(df["Volume"], downcast="integer")
                
                # Set index to datetime
                df.index = pd.DatetimeIndex(df.index)
                
                # Sort by date (most recent first)
                df = df.sort_index(ascending=False)
                
                # Filter based on period
                if period == "1d":
                    cutoff = datetime.now() - timedelta(days=1)
                    df = df[df.index >= cutoff]
                elif period == "1w":
                    cutoff = datetime.now() - timedelta(days=7)
                    df = df[df.index >= cutoff]
                elif period == "1mo":
                    cutoff = datetime.now() - timedelta(days=30)
                    df = df[df.index >= cutoff]
                elif period == "3mo":
                    cutoff = datetime.now() - timedelta(days=90)
                    df = df[df.index >= cutoff]
                elif period == "6mo":
                    cutoff = datetime.now() - timedelta(days=180)
                    df = df[df.index >= cutoff]
                elif period == "1y":
                    cutoff = datetime.now() - timedelta(days=365)
                    df = df[df.index >= cutoff]
                
                print(f"Successfully created DataFrame with {len(df)} rows")
                return df
            
            # If we get here, we didn't get a valid response
            print(f"No time series data found in response for {symbol}")
            return None
            
        except Exception as e:
            print(f"Error getting daily data for {symbol}: {str(e)}")
            return None
            
    def create_synthetic_data(self, symbol):
        """Create synthetic data when all other methods fail"""
        print(f"Creating synthetic data for {symbol}")
        
        # Generate random but somewhat realistic price based on ticker symbol
        # This makes the same ticker always generate similar data
        ticker_value = sum(ord(c) * (i+1) for i, c in enumerate(symbol))
        base_price = max(10, (ticker_value % 1000) + 10)
        
        # Generate quote
        quote = {
            "symbol": symbol,
            "price": base_price,
            "change": round(base_price * 0.005, 2),  # 0.5% change
            "change_percent": 0.5  # 0.5% change
        }
        
        return quote
    
    def create_synthetic_history(self, quote, days=30):
        """Create synthetic historical data"""
        # Generate dates
        today = datetime.now()
        dates = [today - timedelta(days=i) for i in range(days)]
        
        # Generate prices with random walk
        base_price = quote["price"] * 0.98  # Start slightly lower for upward trend
        prices = []
        for i in range(days):
            # Random walk with slight upward bias
            random_factor = random.uniform(-0.01, 0.015)
            price = base_price * (1 + random_factor)
            prices.append(price)
            base_price = price
            
        prices = list(reversed(prices))  # Oldest to newest
        
        # Create dataframe
        hist_data = {
            'Open': prices,
            'High': [p * random.uniform(1.001, 1.01) for p in prices],
            'Low': [p * random.uniform(0.99, 0.999) for p in prices],
            'Close': prices,
            'Adjusted Close': prices,
            'Volume': [random.randint(100000, 2000000) for _ in range(days)]
        }
        
        hist = pd.DataFrame(hist_data, index=pd.DatetimeIndex(dates))
        hist = hist.sort_index(ascending=False)  # Most recent first
        
        return hist


def get_stock_data(ticker, api_key, period="1mo"):
    """Get stock data with fallback to synthetic data"""
    av = AlphaVantageAPI(api_key)
    
    # Try to get real data first
    quote = av.get_quote(ticker)
    hist = None
    is_synthetic = False
    
    if quote:
        print(f"Got real quote data for {ticker}")
        hist = av.get_daily_adjusted(ticker, period)
    else:
        # Generate synthetic data
        print(f"Using synthetic data for {ticker}")
        quote = av.create_synthetic_data(ticker)
        is_synthetic = True
    
    # If history is not available, generate it
    if hist is None or hist.empty:
        print(f"Generating synthetic history for {ticker}")
        hist = av.create_synthetic_history(quote)
        is_synthetic = True
    
    # Create a StockData object
    class StockData:
        def __init__(self, ticker, quote, hist, is_synthetic):
            self.ticker = ticker
            self.info = {
                "regularMarketPrice": quote["price"],
                "shortName": ticker,
                "changePercent": quote["change_percent"]
            }
            self._hist = hist
            self.is_synthetic = is_synthetic
            
        def history(self, period=None):
            return self._hist
    
    return StockData(ticker, quote, hist, is_synthetic)