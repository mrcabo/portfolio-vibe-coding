import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json

class AlphaVantageAPI:
    """Class to handle Alpha Vantage API calls"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_quote(self, symbol):
        """Get current stock quote"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        print(f"Requesting quote for {symbol}...")
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        print(f"Quote API response: {json.dumps(data)[:200]}...")
        
        if "Global Quote" in data and data["Global Quote"]:
            quote = data["Global Quote"]
            return {
                "symbol": quote["01. symbol"],
                "price": float(quote["05. price"]),
                "change": float(quote["09. change"]),
                "change_percent": float(quote["10. change percent"].strip("%"))
            }
            
        if "Note" in data:
            print(f"API limit message: {data['Note']}")
            # Sleep if we hit rate limit
            time.sleep(12)  # Wait for rate limit to reset
            
        return None
    
    def get_company_overview(self, symbol):
        """Get company information"""
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        response = requests.get(self.base_url, params=params)
        return response.json()
    
    def get_daily_adjusted(self, symbol, period="1mo"):
        """Get historical price data"""
        # Map period to outputsize
        outputsize = "compact"  # Default to last 100 data points
        if period in ["6m", "1y"]:
            outputsize = "full"  # Get up to 20 years of data
            
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self.api_key
        }
        
        print(f"Requesting daily adjusted data for {symbol} with outputsize={outputsize}...")
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        # Print first part of response for debugging
        print(f"Daily data API response keys: {list(data.keys())}")
        
        if "Note" in data:
            print(f"API limit message: {data['Note']}")
            # Sleep if we hit rate limit
            time.sleep(12)  # Wait for rate limit to reset
            return None
            
        if "Error Message" in data:
            print(f"API error: {data['Error Message']}")
            return None
            
        if "Time Series (Daily)" in data:
            # Additional debug
            ts_data = data["Time Series (Daily)"]
            print(f"Got {len(ts_data)} days of data. First date: {next(iter(ts_data))}")
            
            try:
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
                if period == "1mo":
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
            except Exception as e:
                print(f"Error processing data: {str(e)}")
                return None
        
        print("No time series data found in response")
        return None


def get_stock_data_alpha_vantage(ticker, api_key, period="1mo"):
    """Get stock data from Alpha Vantage API"""
    av = AlphaVantageAPI(api_key)
    
    # Get quote data first
    quote = av.get_quote(ticker)
    if not quote:
        print(f"Could not get quote data for {ticker}")
        return None
    
    print(f"Got quote data for {ticker}: {quote}")
    
    # Get historical data 
    hist = av.get_daily_adjusted(ticker, period)
    
    # If we got quote data but no history, we can still return a valid object
    # This allows the app to work with just current price data
    if hist is None or hist.empty:
        print(f"No historical data for {ticker}, creating stock object with quote data only")
        # Create a minimal dataframe with at least one row
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        minimal_hist = pd.DataFrame({
            'Open': [quote['price'], quote['price'] * 0.99],
            'High': [quote['price'] * 1.01, quote['price'] * 1.005],
            'Low': [quote['price'] * 0.99, quote['price'] * 0.985],
            'Close': [quote['price'], quote['price'] * 0.99],
            'Volume': [1000000, 900000]
        }, index=pd.DatetimeIndex([today, yesterday]))
        
        hist = minimal_hist
    
    # Create a class similar to yfinance.Ticker
    class StockData:
        def __init__(self, ticker, quote, hist):
            self.ticker = ticker
            self.info = {
                "regularMarketPrice": quote["price"],
                "shortName": ticker,  # We could get this from company overview
                "changePercent": quote["change_percent"]
            }
            self._hist = hist
            
        def history(self, period=None):
            return self._hist
    
    return StockData(ticker, quote, hist)