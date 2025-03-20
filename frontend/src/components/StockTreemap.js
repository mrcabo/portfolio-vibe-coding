import React from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';

export const StockTreemap = ({ data }) => {
  // Transform data for treemap visualization with proper hierarchy
  const transformedData = data.map(stock => ({
    name: stock.ticker,
    size: stock.value,
    percentChange: stock.percentChange,
    shares: stock.shares,
    price: stock.currentPrice,
    value: stock.value,
  }));

  // Ensure we have only one unique entry per ticker
  const uniqueStocks = Object.values(
    transformedData.reduce((acc, item) => {
      acc[item.name] = item;
      return acc;
    }, {})
  );

  // Custom tooltip content
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p><strong>{data.name}</strong></p>
          <p>Shares: {data.shares}</p>
          <p>Price: ${data.price?.toFixed(2)}</p>
          <p>Value: ${data.value?.toFixed(2)}</p>
          <p>Change: {data.percentChange?.toFixed(2)}%</p>
        </div>
      );
    }
    return null;
  };

  // Color based on percent change (red for negative, green for positive)
  const getColor = (percentChange) => {
    if (percentChange > 0) {
      const intensity = Math.min(percentChange * 5, 100);
      return `rgba(0, ${Math.round(128 + intensity)}, 0, 0.9)`;
    } else {
      const intensity = Math.min(Math.abs(percentChange) * 5, 100);
      return `rgba(${Math.round(200 + intensity / 2)}, 0, 0, 0.9)`;
    }
  };

  // Custom content for treemap tile
  const CustomTreemapContent = (props) => {
    const { x, y, width, height, name, depth } = props;

    // Skip rendering if width or height is too small or if it's the root node
    if (width < 30 || height < 30 || name === 'root' || depth === 0) return null;

    // Get percentChange and value from the payload data
    // In Recharts, root.children have the actual stock data
    const stockData = props.root.children.find(item => item.name === name);
    if (!stockData) return null;

    const { percentChange, value } = stockData;

    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          style={{
            fill: getColor(percentChange),
            stroke: '#fff',
            strokeWidth: 2,
          }}
        />
        <text
          x={x + width / 2}
          y={y + height / 2 - 12}
          textAnchor="middle"
          fill="#fff"
          fontSize={14}
          fontWeight="bold"
        >
          {name}
        </text>
        <text
          x={x + width / 2}
          y={y + height / 2 + 12}
          textAnchor="middle"
          fill="#fff"
          fontSize={12}
        >
          {value ? `$${Math.round(value)}` : ''}
        </text>
      </g>
    );
  };

  return (
    <div className="treemap-container" style={{ width: '100%', height: 400 }}>
      <h3>Portfolio Treemap</h3>
      {uniqueStocks.length > 0 ? (
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={uniqueStocks}
            dataKey="size"
            aspectRatio={4 / 3}
            stroke="#fff"
            content={<CustomTreemapContent />}
          >
            <Tooltip content={<CustomTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      ) : (
        <div className="no-data">No stocks in portfolio</div>
      )}
    </div>
  );
};