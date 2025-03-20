import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AddStockForm } from './components/AddStockForm';
import { StockTreemap } from './components/StockTreemap';
import { PortfolioTable } from './components/PortfolioTable';
import './App.css';

const API_URL = 'http://127.0.0.1:5001/api';

function App() {
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [warning, setWarning] = useState(null);
  const [period, setPeriod] = useState('1m');
  const [activeTab, setActiveTab] = useState('portfolio'); // 'portfolio' or 'manage'
  const [editingStock, setEditingStock] = useState(null);

  // Fetch portfolio data
  const fetchPortfolioData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/portfolio/data?period=${period}`);

      // Check if the response structure has changed (data + warning)
      if (response.data.data) {
        setPortfolio(response.data.data);
        setWarning(response.data.warning);
      } else {
        // Handle backward compatibility with old API format
        setPortfolio(response.data);
        setWarning(null);
      }

      setError(null);
    } catch (err) {
      console.error('Error fetching portfolio data:', err);
      setError('Failed to fetch portfolio data. Please try again.');
      setWarning(null);
    } finally {
      setLoading(false);
    }
  };

  // Initial load and when period changes
  useEffect(() => {
    fetchPortfolioData();
    // Set up a refresh interval (every 5 minutes)
    const intervalId = setInterval(fetchPortfolioData, 5 * 60 * 1000);

    // Clean up interval
    return () => clearInterval(intervalId);
  }, [period]);

  // Add stock to portfolio
  const addStock = async (ticker, shares) => {
    try {
      setError(null); // Clear any previous errors
      setWarning(null); // Clear any previous warnings

      const response = await axios.post(`${API_URL}/portfolio`, { ticker, shares });
      console.log('Success response:', response.data);

      // Check for any warnings in the response
      if (response.data.warning) {
        setWarning(response.data.warning);
      }

      fetchPortfolioData();
      setActiveTab('portfolio'); // Switch to portfolio view after adding
    } catch (err) {
      console.error('Error adding stock:', err);
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.log('Error data:', err.response.data);
        console.log('Error status:', err.response.status);
        setError(err.response?.data?.error || `Server error: ${err.response.status}`);
      } else if (err.request) {
        // The request was made but no response was received
        console.log('Error request:', err.request);
        setError('No response from server. Is the backend running?');
      } else {
        // Something happened in setting up the request that triggered an Error
        setError(`Request error: ${err.message}`);
      }
    }
  };

  // Remove stock from portfolio
  const removeStock = async (ticker) => {
    try {
      await axios.delete(`${API_URL}/portfolio/${ticker}`);
      fetchPortfolioData();
    } catch (err) {
      console.error('Error removing stock:', err);
      setError(err.response?.data?.error || 'Failed to remove stock');
    }
  };

  // Edit stock shares
  const editStockShares = async (ticker, newShares) => {
    try {
      setError(null);
      setWarning(null);

      // First delete the stock
      await axios.delete(`${API_URL}/portfolio/${ticker}`);

      // Then add it back with the new shares count
      const response = await axios.post(`${API_URL}/portfolio`, {
        ticker,
        shares: parseFloat(newShares)
      });

      if (response.data.warning) {
        setWarning(response.data.warning);
      }

      fetchPortfolioData();
      setEditingStock(null); // Close the edit mode
    } catch (err) {
      console.error('Error updating stock shares:', err);
      setError('Failed to update shares. Please try again.');
    }
  };

  // Handle period change
  const handlePeriodChange = (e) => {
    setPeriod(e.target.value);
  };

  // Calculate total portfolio value
  const totalValue = portfolio.reduce((sum, stock) => sum + stock.value, 0);

  return (
    <div className="app">
      <header>
        <h1>Investment Portfolio Tracker</h1>
      </header>

      <div className="tabs">
        <button
          className={`tab-button ${activeTab === 'portfolio' ? 'active' : ''}`}
          onClick={() => setActiveTab('portfolio')}
        >
          Portfolio
        </button>
        <button
          className={`tab-button ${activeTab === 'manage' ? 'active' : ''}`}
          onClick={() => setActiveTab('manage')}
        >
          Add Stocks
        </button>
      </div>

      {activeTab === 'portfolio' && (
        <div className="period-selector">
          <label htmlFor="period">Time Period:</label>
          <select
            id="period"
            value={period}
            onChange={handlePeriodChange}
          >
            <option value="1d">1 Day</option>
            <option value="1w">1 Week</option>
            <option value="1m">1 Month</option>
            <option value="3m">3 Months</option>
            <option value="6m">6 Months</option>
            <option value="1y">1 Year</option>
          </select>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}
      {warning && <div className="warning-message">{warning}</div>}

      {activeTab === 'manage' && (
        <div className="manage-stocks-container">
          <AddStockForm onAddStock={addStock} />
        </div>
      )}

      {activeTab === 'portfolio' && (
        loading ? (
          <div className="loading">Loading portfolio data...</div>
        ) : (
          <>
            {portfolio.length === 0 ? (
              <div className="empty-portfolio">
                <p>Your portfolio is empty. Add some stocks to get started!</p>
                <button
                  className="add-stock-button"
                  onClick={() => setActiveTab('manage')}
                >
                  Add Stocks
                </button>
              </div>
            ) : (
              <>
                <div className="portfolio-summary">
                  <h2>Portfolio Value: ${totalValue.toFixed(2)}</h2>
                </div>

                <div className="visualization">
                  <StockTreemap data={portfolio} />
                </div>

                <div className="portfolio-table">
                  <PortfolioTable
                    portfolio={portfolio}
                    onRemoveStock={removeStock}
                    onEditShares={editStockShares}
                    editingStock={editingStock}
                    setEditingStock={setEditingStock}
                  />
                </div>
              </>
            )}
          </>
        )
      )}
    </div>
  );
}

export default App;