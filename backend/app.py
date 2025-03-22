from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import time
from datetime import datetime, timedelta
import random

# Import our Alpha Vantage module - simplified approach
from alpha_vantage_api import get_stock_data

app = Flask(__name__)
# Enable CORS with more explicit settings
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "OPTIONS"]}})

# Alpha Vantage API key
ALPHA_VANTAGE_API_KEY = "Z8P7GCDNP67S7OD9"

# Add a simple route to verify the API is reachable
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running", "data_source": "Alpha Vantage with Fallbacks"})

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

def get_cached_stock_data(ticker, period="1mo"):
    """Get stock data with caching"""
    # Check cache first
    current_time = time.time()
    if ticker in STOCK_CACHE:
        cached_data, timestamp, synthetic_flag = STOCK_CACHE[ticker]
        # If cache is still valid (less than CACHE_EXPIRY seconds old)
        if current_time - timestamp < CACHE_EXPIRY and not synthetic_flag:
            print(f"Using cached data for {ticker}")
            return cached_data, None
    
    # Not in cache or cache expired or using synthetic data, fetch from API
    try:
        # Use the simplified API approach
        stock = get_stock_data(ticker, ALPHA_VANTAGE_API_KEY, period)
        
        # Check if we got a valid object
        if not stock or not hasattr(stock, 'info'):
            return None, f"Could not get data for {ticker}"
        
        warning = None
        if hasattr(stock, 'is_synthetic') and stock.is_synthetic:
            warning = f"Using estimated data for {ticker}. Real-time data unavailable."
            
        # Store in cache - include the synthetic flag
        STOCK_CACHE[ticker] = (stock, current_time, stock.is_synthetic if hasattr(stock, 'is_synthetic') else False)
        return stock, warning
            
    except Exception as e:
        print(f"Error fetching {ticker}: {str(e)}")
        
        # If we have cached data (even if expired), return it with a warning
        if ticker in STOCK_CACHE:
            cached_data, old_timestamp, synthetic_flag = STOCK_CACHE[ticker]
            cache_age = current_time - old_timestamp
            cache_minutes = round(cache_age / 60)
            
            return cached_data, f"Using {cache_minutes} minute old data. API request failed."
        
        return None, f"Could not retrieve data for {ticker}: {str(e)}"

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
    
    # Check if stock exists
    try:
        stock, warning = get_cached_stock_data(ticker)
        
        # Check if we got a valid stock object back
        if stock is None:
            # We tried our best but couldn't get stock data
            return jsonify({
                'error': warning or f'Could not retrieve data for {ticker}'
            }), 503
        
        # Add to portfolio
        portfolio = read_portfolio()
        
        # Check if stock already exists in portfolio
        for item in portfolio:
            if item['ticker'] == ticker:
                item['shares'] += shares
                write_portfolio(portfolio)
                return jsonify({
                    'message': f'Updated shares for {ticker}',
                    'warning': warning
                }), 200
        
        # Add new stock
        portfolio.append({
            'ticker': ticker,
            'shares': shares
        })
        
        write_portfolio(portfolio)
        return jsonify({
            'message': f'Added {ticker} to portfolio',
            'warning': warning
        }), 201
            
    except Exception as e:
        print(f"Exception when fetching {ticker}:", str(e))
        return jsonify({'error': f'Error fetching stock data: {str(e)}'}), 500

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
    
    for item in portfolio:
        ticker = item['ticker']
        shares = item['shares']
        
        try:
            # Get stock data with caching
            stock, error_message = get_cached_stock_data(ticker, period)
            
            if error_message:
                has_warning = True
                warning_message = error_message
            
            # Skip this stock if we couldn't get data
            if stock is None:
                print(f"Skipping {ticker} in portfolio data - could not retrieve data")
                continue
            
            # Get price data
            info = stock.info
            current_price = info.get('regularMarketPrice', 0)
            
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
            if abs(percent_change) > 1:
                normalized_percent_change = percent_change / 100
            else:
                normalized_percent_change = percent_change
                
            result.append({
                'ticker': ticker,
                'shares': shares,
                'currentPrice': current_price,
                'value': value,
                'percentChange': normalized_percent_change
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