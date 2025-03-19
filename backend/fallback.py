# Add to your backend folder as fallback.py

"""
This module provides fallback data when Yahoo Finance API is unavailable
due to rate limiting or other issues.
"""

FALLBACK_STOCKS = {
    "AAPL": {
        "name": "Apple Inc.",
        "price": 180.25,
        "change": 2.5
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "price": 340.12,
        "change": 1.8
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "price": 137.45,
        "change": -0.7
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "price": 132.90,
        "change": 0.3
    },
    "META": {
        "name": "Meta Platforms, Inc.",
        "price": 310.75,
        "change": 3.2
    },
    "TSLA": {
        "name": "Tesla, Inc.",
        "price": 245.60,
        "change": -2.1
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "price": 430.35,
        "change": 4.2
    },
    "BRK-B": {
        "name": "Berkshire Hathaway Inc.",
        "price": 375.80,
        "change": 0.5
    },
    "JPM": {
        "name": "JPMorgan Chase & Co.",
        "price": 155.40,
        "change": -0.9
    },
    "JNJ": {
        "name": "Johnson & Johnson",
        "price": 162.15,
        "change": 1.1
    }
}

def get_fallback_stock_data(ticker):
    """
    Get fallback data for a specific stock if Yahoo Finance API is unavailable.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        dict: Stock data including price and change percentage
              or None if ticker not in fallback data
    """
    return FALLBACK_STOCKS.get(ticker.upper())