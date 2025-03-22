from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import time
from datetime import datetime, timedelta
import random

# Import our Yahoo Finance module instead of Alpha Vantage
from yahoo_finance_api import get_stock_data_yahoo

app = Flask(__name__)
# Enable CORS with more explicit settings
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "OPTIONS"]}})

# Add a simple route to verify the API is reachable
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running", "data_source": "Yahoo Finance"})

PORTFOLIO_FILE = os.environ.get('PORTFOLIO_PATH', 'portfolio.json')

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
CACHE_EXPIRY = 300  # 5 minutes cache expiry

def get_stock_data(ticker, max_retries=3):
    """Get stock data with retries and caching"""
    # Check cache first
    current_time = time.time()
    if ticker in STOCK_CACHE:
        cached_data, timestamp = STOCK_CACHE[ticker]
        # If cache is still valid (less than CACHE_EXPIRY seconds old)
        if current_time - timestamp < CACHE_EXPIRY:
            print(f"Using cached data for {ticker}")
            return cached_data, None
    
    # Not in cache or cache expired, fetch from API
    retries = 0
    error_message = None
    while retries < max_retries:
        try:
            print(f"Fetching data for {ticker} from Yahoo Finance (attempt {retries+1}/{max_retries})...")
            # Using Yahoo Finance instead of Alpha Vantage
            stock = get_stock_data_yahoo(ticker)
            
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
            return stock, None
            
        except Exception as e:
            retries += 1
            error_message = str(e)
            print(f"Error fetching {ticker} (attempt {retries}/{max_retries}): {error_message}")
            
            # Add exponential backoff with jitter
            wait_time = (2 ** retries) + random.uniform(0, 1)
            print(f"Waiting {wait_time:.2f} seconds before retry...")
            time.sleep(wait_time)
    
    # All retries failed, return cached data if available with an error message
    if ticker in STOCK_CACHE:
        # Return expired cache data but with a warning
        cached_data, old_timestamp = STOCK_CACHE[ticker]
        cache_age = current_time - old_timestamp
        cache_minutes = round(cache_age / 60)
        
        print(f"Returning stale cache data for {ticker} ({cache_minutes} minutes old)")
        return cached_data, f"Using {cache_minutes} minute old data. API request failed."
    
    # No cache available
    return None, error_message or "Could not retrieve data"

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
        stock, error_message = get_stock_data(ticker)
        
        # Check if we got a valid stock object back
        if stock is None:
            # We tried our best but couldn't get stock data
            return jsonify({
                'error': error_message or f'Could not retrieve data for {ticker} after multiple attempts.'
            }), 503
        
        # Try to access regularMarketPrice
        has_price = False
        info = stock.info
        
        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
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
            return jsonify({
                'message': f'Updated shares for {ticker}',
                'warning': error_message
            }), 200
    
    # Add new stock
    portfolio.append({
        'ticker': ticker,
        'shares': shares
    })
    
    write_portfolio(portfolio)
    return jsonify({
        'message': f'Added {ticker} to portfolio',
        'warning': error_message
    }), 201

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
    
    portfolio = read_portfolio()
    result = []
    has_warning = False
    warning_message = None
    
    if not portfolio:
        return jsonify({"data": [], "warning": None}), 200
    
    # Use individual requests with retry logic
    for item in portfolio:
        ticker = item['ticker']
        shares = item['shares']
        
        try:
            # Get stock data with retry logic
            stock, error_message = get_stock_data(ticker)
            
            if error_message:
                has_warning = True
                warning_message = error_message
            
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
            
            # IMPORTANT: Normalize percentChange to decimal format (0.05 for 5%)
            # This ensures consistent format across all stock data
            if abs(percent_change) > 1:
                normalized_percent_change = percent_change / 100
            else:
                normalized_percent_change = percent_change
                
            result.append({
                'ticker': ticker,
                'shares': shares,
                'currentPrice': current_price,
                'value': value,
                'percentChange': normalized_percent_change  # Using normalized value
            })
            
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
            # Continue with other stocks even if one fails
            has_warning = True
            warning_message = f"Error processing some stocks. Data may be incomplete."
            continue
    
    return jsonify({
        "data": result,
        "warning": warning_message if has_warning else None
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)