from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import yfinance as yf
from datetime import datetime, timedelta

app = Flask(__name__)
# Enable CORS with more explicit settings
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "OPTIONS"]}})

# Add a simple route to verify the API is reachable
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running"})

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
        stock = yf.Ticker(ticker)
        info = stock.info
        print(f"Stock info for {ticker}:", info)  # Debug - Print stock info
        
        # Try multiple ways to get the stock price
        if 'regularMarketPrice' not in info:
            # Try alternative ways to get price
            print(f"Missing regularMarketPrice for {ticker}, trying alternatives")
            
            # Alternative 1: Try to get history
            hist = stock.history(period="1d")
            if not hist.empty and 'Close' in hist.columns and len(hist['Close']) > 0:
                print(f"Got price from history: {hist['Close'].iloc[-1]}")
                # We found a price, so we're good to continue
            else:
                # Alternative 2: Check if we can find the symbol
                print(f"Could not get history for {ticker}, checking if valid symbol")
                # If we can't verify the stock at all, return error
                return jsonify({'error': f'Could not verify ticker symbol: {ticker}'}), 404
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
    
    # Map frontend period to yfinance period format
    period_map = {
        '1m': '1mo',
        '3m': '3mo',
        '6m': '6mo',
        '1y': '1y'
    }
    
    yf_period = period_map.get(period, '1mo')
    
    portfolio = read_portfolio()
    result = []
    
    if not portfolio:
        return jsonify([]), 200
    
    # Get all tickers
    tickers = [item['ticker'] for item in portfolio]
    
    try:
        # Fetch data for all tickers at once
        stocks_data = yf.download(tickers, period=yf_period, group_by='ticker')
        
        for item in portfolio:
            ticker = item['ticker']
            shares = item['shares']
            
            # Handle single ticker case differently
            if len(tickers) == 1:
                current_price = stocks_data['Close'][-1]
                initial_price = stocks_data['Close'][0]
            else:
                current_price = stocks_data[ticker]['Close'][-1]
                initial_price = stocks_data[ticker]['Close'][0]
            
            value = current_price * shares
            percent_change = ((current_price - initial_price) / initial_price) * 100
            
            result.append({
                'ticker': ticker,
                'shares': shares,
                'currentPrice': current_price,
                'value': value,
                'percentChange': percent_change
            })
            
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': f'Error fetching stock data: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)