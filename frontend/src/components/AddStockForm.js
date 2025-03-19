import React, { useState } from 'react';

export const AddStockForm = ({ onAddStock }) => {
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!ticker || !shares) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      await onAddStock(ticker, parseFloat(shares));
      // Reset form
      setTicker('');
      setShares('');
    } catch (error) {
      console.error('Error adding stock:', error);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <form className="add-stock-form" onSubmit={handleSubmit}>
      <h3>Add Stock</h3>
      
      <div className="form-group">
        <label htmlFor="ticker">Ticker Symbol:</label>
        <input
          type="text"
          id="ticker"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="e.g., AAPL"
          required
        />
      </div>
      
      <div className="form-group">
        <label htmlFor="shares">Number of Shares:</label>
        <input
          type="number"
          id="shares"
          value={shares}
          onChange={(e) => setShares(e.target.value)}
          placeholder="e.g., 10"
          step="0.01"
          min="0.01"
          required
        />
      </div>
      
      <button 
        type="submit" 
        disabled={isSubmitting || !ticker || !shares}
      >
        {isSubmitting ? 'Adding...' : 'Add Stock'}
      </button>
    </form>
  );
};