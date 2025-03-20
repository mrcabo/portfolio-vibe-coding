import React, { useState } from 'react';

export const PortfolioTable = ({
  portfolio,
  onRemoveStock,
  onEditShares,
  editingStock,
  setEditingStock
}) => {
  const [newShares, setNewShares] = useState('');

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

  // Handle edit button click
  const handleEditClick = (stock) => {
    setEditingStock(stock.ticker);
    setNewShares(stock.shares.toString());
  };

  // Handle save button click
  const handleSaveClick = (ticker) => {
    if (newShares && !isNaN(parseFloat(newShares)) && parseFloat(newShares) > 0) {
      onEditShares(ticker, newShares);
    }
  };

  // Handle cancel button click
  const handleCancelClick = () => {
    setEditingStock(null);
    setNewShares('');
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
              <td>
                {editingStock === stock.ticker ? (
                  <input
                    type="number"
                    className="shares-input"
                    value={newShares}
                    onChange={(e) => setNewShares(e.target.value)}
                    min="0.01"
                    step="0.01"
                    required
                  />
                ) : (
                  stock.shares
                )}
              </td>
              <td>${stock.currentPrice.toFixed(2)}</td>
              <td>${stock.value.toFixed(2)}</td>
              <td>{formatPercentChange(stock.percentChange)}</td>
              <td>
                {editingStock === stock.ticker ? (
                  <div className="edit-actions">
                    <button
                      className="save-btn"
                      onClick={() => handleSaveClick(stock.ticker)}
                      disabled={!newShares || isNaN(parseFloat(newShares)) || parseFloat(newShares) <= 0}
                    >
                      Save
                    </button>
                    <button
                      className="cancel-btn"
                      onClick={handleCancelClick}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="stock-actions">
                    <button
                      className="edit-btn"
                      onClick={() => handleEditClick(stock)}
                    >
                      Edit
                    </button>
                    <button
                      className="remove-btn"
                      onClick={() => handleRemove(stock.ticker)}
                    >
                      Remove
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};