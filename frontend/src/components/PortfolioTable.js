import React from 'react';

export const PortfolioTable = ({ portfolio, onRemoveStock }) => {
  // Sort portfolio by value (largest first)
  const sortedPortfolio = [...portfolio].sort((a, b) => b.value - a.value);
  
  // Format percent change with color
  const formatPercentChange = (percentChange) => {
    const color = percentChange >= 0 ? 'green' : 'red';
    const sign = percentChange >= 0 ? '+' : '';
    return (
      <span style={{ color }}>
        {sign}{percentChange.toFixed(2)}%
      </span>
    );
  };
  
  // Handle remove button click
  const handleRemove = (ticker) => {
    if (window.confirm(`Are you sure you want to remove ${ticker} from your portfolio?`)) {
      onRemoveStock(ticker);
    }
  };
  
  return (
    <div className="portfolio-table">
      <h3>Portfolio Details</h3>
      <table>
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Shares</th>
            <th>Price</th>
            <th>Value</th>
            <th>Change</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sortedPortfolio.map((stock) => (
            <tr key={stock.ticker}>
              <td>{stock.ticker}</td>
              <td>{stock.shares}</td>
              <td>${stock.currentPrice.toFixed(2)}</td>
              <td>${stock.value.toFixed(2)}</td>
              <td>{formatPercentChange(stock.percentChange)}</td>
              <td>
                <button 
                  className="remove-btn"
                  onClick={() => handleRemove(stock.ticker)}
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};