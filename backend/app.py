from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import time
import random
from datetime import datetime, timedelta

# Import our Alpha Vantage module
from alpha_vantage_api import get_stock_data_alpha_vantage

# Import fallback data
try:
    from fallback import get_fallback_stock_data
    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False
    print("Fallback data not available. This is fine for normal operation.")

# Alpha Vantage API key
ALPHA_VANTAGE_API_KEY = "Z8P7GCDNP67S7OD9"

app = Flask(__name__)
# Enable CORS with more explicit settings
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "OPTIONS"]}})

# Add a simple route to verify the API is reachable
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running", "data_source": "Alpha Vantage"})

PORTFOLIO_FILE = 'portfolio.json'

# Create portfolio file if it doesn't exist
if not os.path.exists(PORTFOLIO_FILE):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump([], f)

def read_portfolio():
    with open(PORTFOLIO_FILE, 'r') as f:
        return json.load(f)

def write_portfolio(portfolio):
    try:
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(portfolio, f, indent=2)
        print(f"Successfully wrote to {PORTFOLIO_FILE}")
    except Exception as e:
        print(f"Error writing to portfolio file: {str(e)}")
        raise

# Cache for stock data to reduce API calls
STOCK_CACHE = {}
CACHE_EXPIRY = 300  # 5 minutes cache expiry - increased for Alpha Vantage's rate limits

def get_stock_data(ticker, max_retries=3):
    """Get stock data with retries and caching to handle rate limits"""
    # Check cache first
    current_time = time.time()
    if ticker in STOCK_CACHE:
        cached_data, timestamp = STOCK_CACHE[ticker]
        # If cache is still valid (less than CACHE_EXPIRY seconds old)
        if current_time - timestamp < CACHE_EXPIRY:
            print(f"Using cached data for {ticker}")
            return cached_data
    
    # Not in cache or cache expired, fetch from API
    retries = 0
    while retries < max_retries:
        try:
            print(f"Fetching data for {ticker} from Alpha Vantage (attempt {retries+1}/{max_retries})...")
            stock = get_stock_data_alpha_vantage(ticker, ALPHA_VANTAGE_API_KEY)
            
            # Verify we got some valid data
            if not stock or not hasattr(stock, 'info'):
                print(f"Got empty info for {ticker}, retrying...")
                raise ValueError(f"Empty info for {ticker}")
                
            # Also check if we have price data one way or another
            if not stock.info.get('regularMarketPrice'):
                print(f"No price data for {ticker}, retrying...")
                raise ValueError(f"No price data for {ticker}")
                
            # Store in cache
            STOCK_CACHE[ticker] = (stock, current_time)
            return stock
            
        except Exception as e:
            retries += 1
            print(f"Error fetching {ticker} (attempt {retries}/{max_retries}): {str(e)}")
            
            # Check if this is related to API limits
            if "api call frequency" in str(e).lower() or "note" in str(e).lower():
                # Rate limited - add exponential backoff with jitter
                wait_time = (2 ** retries) + random.uniform(0, 1)
                print(f"Rate limited. Waiting {wait_time:.2f} seconds before retry...")
                time.sleep(wait_time)
            elif retries >= max_retries:
                # We've tried max_retries times, use fallback data
                break
            else:
                # Other error, short pause before retry
                time.sleep(2)
    
    # All retries failed, check if fallback data is available
    if FALLBACK_AVAILABLE:
        fallback = get_fallback_stock_data(ticker)
        if fallback:
            print(f"Using fallback data for {ticker}")
            # Create a minimal fake stock object with the necessary fields
            class FallbackStock:
                def __init__(self, ticker, fallback_data):
                    self.ticker = ticker
                    self.info = {
                        'regularMarketPrice': fallback_data['price'],
                        'shortName': fallback_data['name']
                    }
                    self._fallback = True
                    self._fallback_data = fallback_data
                    
                def history(self, period=None):
                    # Create a minimal fake history with just start and end prices
                    import pandas as pd
                    import numpy as np
                    
                    # Create a date range based on period
                    end_date = datetime.now()
                    if period == '1d':
                        periods = 2
                        start_date = end_date - timedelta(days=1)
                    elif period == '1mo':
                        periods = 22
                        start_date = end_date - timedelta(days=30)
                    elif period == '3mo':
                        periods = 66
                        start_date = end_date - timedelta(days=90)
                    elif period == '6mo':
                        periods = 132
                        start_date = end_date - timedelta(days=180)
                    elif period == '1y':
                        periods = 253
                        start_date = end_date - timedelta(days=365)
                    else:
                        periods = 22
                        start_date = end_date - timedelta(days=30)
                    
                    # Create date range
                    date_range = pd.date_range(start=start_date, end=end_date, periods=periods)
                    
                    # Calculate price path based on current price and change percentage
                    current_price = self._fallback_data['price']
                    change_pct = self._fallback_data['change']
                    
                    # Work backward to get the starting price
                    start_price = current_price / (1 + change_pct/100)
                    
                    # Generate a somewhat realistic price path
                    price_path = np.linspace(start_price, current_price, periods)
                    # Add some noise to make it look more realistic
                    noise = np.random.normal(0, current_price * 0.01, periods)
                    price_path = price_path + noise
                    # Ensure the final price is the current price
                    price_path[-1] = current_price
                    
                    # Create DataFrame
                    df = pd.DataFrame({
                        'Open': price_path,
                        'High': price_path * 1.005,
                        'Low': price_path * 0.995,
                        'Close': price_path,
                        'Volume': np.random.randint(1000000, 10000000, periods)
                    }, index=date_range)
                    
                    return df
            
            # Return the fallback stock object
            fallback_stock = FallbackStock(ticker, fallback)
            STOCK_CACHE[ticker] = (fallback_stock, current_time)
            return fallback_stock
    
    # If we get here, all retries failed and no fallback was available
    print(f"All attempts to fetch {ticker} failed and no fallback available")
    return None

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    portfolio = read_portfolio()
    return jsonify(portfolio)

@app.route('/api/portfolio', methods=['POST'])
def add_stock():
    stock_data = request.json
    
    # Validate input
    required_fields = ['ticker', 'shares']
    for field in required_fields:
        if field not in stock_data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    ticker = stock_data['ticker'].upper()
    shares = float(stock_data['shares'])
    
    # Check if stock exists with retry logic
    try:
        stock = get_stock_data(ticker)
        
        # Check if we got a valid stock object back
        if stock is None:
            # We tried our best but couldn't get stock data
            return jsonify({'error': f'Could not retrieve data for {ticker} after multiple attempts. Alpha Vantage may be rate limiting requests.'}), 503
        
        # Try to access regularMarketPrice in different ways
        has_price = False
        info = stock.info
        
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            has_price = True
        elif 'currentPrice' in info and info['currentPrice'] is not None:
            has_price = True
        else:
            # Try to get price from history
            hist = stock.history()
            if hist is not None and not hist.empty and 'Close' in hist.columns and len(hist['Close']) > 0:
                has_price = True
        
        if not has_price:
            return jsonify({'error': f'Could not find price data for ticker: {ticker}'}), 404
            
    except Exception as e:
        print(f"Exception when fetching {ticker}:", str(e))
        return jsonify({'error': f'Error fetching stock data: {str(e)}'}), 500
    
    # Add to portfolio
    portfolio = read_portfolio()
    
    # Check if stock already exists in portfolio
    for item in portfolio:
        if item['ticker'] == ticker:
            item['shares'] += shares
            write_portfolio(portfolio)
            return jsonify({'message': f'Updated shares for {ticker}'}), 200
    
    # Add new stock
    portfolio.append({
        'ticker': ticker,
        'shares': shares
    })
    
    write_portfolio(portfolio)
    return jsonify({'message': f'Added {ticker} to portfolio'}), 201

@app.route('/api/portfolio/<ticker>', methods=['DELETE'])
def remove_stock(ticker):
    ticker = ticker.upper()
    portfolio = read_portfolio()
    
    initial_length = len(portfolio)
    portfolio = [item for item in portfolio if item['ticker'] != ticker]
    
    if len(portfolio) == initial_length:
        return jsonify({'error': f'Stock {ticker} not found in portfolio'}), 404
    
    write_portfolio(portfolio)
    return jsonify({'message': f'Removed {ticker} from portfolio'}), 200

@app.route('/api/portfolio/data', methods=['GET'])
def get_portfolio_data():
    period = request.args.get('period', '1mo')
    
    # Map frontend period to Alpha Vantage period format
    period_map = {
        '1m': '1mo',
        '3m': '3mo',
        '6m': '6mo',
        '1y': '1y'
    }
    
    av_period = period_map.get(period, '1mo')
    
    portfolio = read_portfolio()
    result = []
    
    if not portfolio:
        return jsonify([]), 200
    
    # Get all tickers
    tickers = [item['ticker'] for item in portfolio]
    
    # Use individual requests with retry logic instead of batch to avoid rate limits
    for item in portfolio:
        ticker = item['ticker']
        shares = item['shares']
        
        try:
            # Get stock data with retry logic
            stock = get_stock_data(ticker)
            
            # Skip this stock if we couldn't get data
            if stock is None:
                print(f"Skipping {ticker} in portfolio data - could not retrieve data")
                continue
            
            # Get price data
            info = stock.info
            current_price = info.get('regularMarketPrice')
            
            # Get historical data for the specified period
            hist = stock.history()
            
            if hist is None or hist.empty:
                initial_price = current_price  # No change if we only have current
                percent_change = 0  # Default to no change
            else:
                # We have historical data, get first and last price
                if len(hist) > 1:
                    current_price = hist['Close'].iloc[0]  # Most recent is first
                    initial_price = hist['Close'].iloc[-1]  # Oldest is last
                    percent_change = ((current_price - initial_price) / initial_price) * 100
                else:
                    # Only have one data point
                    initial_price = current_price
                    percent_change = 0
            
            value = current_price * shares
            
            result.append({
                'ticker': ticker,
                'shares': shares,
                'currentPrice': current_price,
                'value': value,
                'percentChange': percent_change
            })
            
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
            # Continue with other stocks even if one fails
            continue
            
    return jsonify(result), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)