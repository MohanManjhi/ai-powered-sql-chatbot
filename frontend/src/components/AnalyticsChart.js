import React, { useState, useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
import './AnalyticsChart.css';

const AnalyticsChart = ({ data, question, sql, onClose, initialChartType = 'auto' }) => {
  const [chartType, setChartType] = useState(initialChartType || 'auto');
  const [chartInstance, setChartInstance] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [exportFormat, setExportFormat] = useState('csv');
  const [exportFilename, setExportFilename] = useState('');
  const [chartData, setChartData] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const chartRef = useRef(null);

  useEffect(() => {
    if (data && data.length > 0) {
      generateChart();
    }
    if (question) {
      const cleanQuestion = question.replace(/[^a-zA-Z0-9\s]/g, '').substring(0, 30);
      setExportFilename(cleanQuestion || 'data_export');
    }
  }, [data, chartType]);

  useEffect(() => {
    if (initialChartType && initialChartType !== chartType) {
      setChartType(initialChartType);
    }
  }, [initialChartType]);

  useEffect(() => {
    return () => {
      if (chartInstance) chartInstance.destroy();
    };
  }, []);

  const generateChart = async () => {
    if (!data || data.length === 0) return;
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5001/api/analytics/chart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, chart_type: chartType, rows: data }),
      });
      const result = await response.json();
      if (result.success) {
        setChartData(result.chart_data);
        setSuggestions(result.suggestions || []);
        renderChart(result.chart_data);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const renderChart = (chartConfig) => {
    if (chartInstance) chartInstance.destroy();
    if (chartRef.current && chartConfig) {
      const ctx = chartRef.current.getContext('2d');
      const newChart = new Chart(ctx, chartConfig);
      setChartInstance(newChart);
    }
  };

  const handleExport = async () => {
    if (!data || data.length === 0) return;
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5001/api/analytics/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: data, format: exportFormat, filename: exportFilename }),
      });
      const result = await response.json();
      if (result.success) {
        const link = document.createElement('a');
        link.href = `http://localhost:5001${result.download_url}`;
        link.download = result.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!data || data.length === 0) return null;

  return (
    <div className="analytics-inline">
      <div className="analytics-inline-content">
        <div className="chart-container">
          {isLoading ? (
            <div className="chart-loading">
              <div className="loading-spinner"></div>
              <p>Generating chart...</p>
            </div>
          ) : (
            <>
              <canvas ref={chartRef} className="chart-canvas"></canvas>
              {chartData && chartData.error && (
                <div className="chart-error">
                  <p>❌ {chartData.error}</p>
                  <p>Try asking for a different chart type.</p>
                </div>
              )}
            </>
          )}
        </div>

        <div className="data-summary">
          <div className="summary-item"><strong>📊 Data Points:</strong> {data.length}</div>
          <div className="summary-item"><strong>🔢 Columns:</strong> {data[0] ? Object.keys(data[0]).length : 0}</div>
        </div>

        <div className="chart-controls">
          <div className="control-group">
            <label>Export Format:</label>
            <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value)} disabled={isLoading}>
              <option value="csv">📄 CSV</option>
              <option value="excel">📊 Excel</option>
              <option value="json">🔧 JSON</option>
            </select>
          </div>
          <div className="control-group">
            <label>Filename:</label>
            <input type="text" value={exportFilename} onChange={(e) => setExportFilename(e.target.value)} placeholder="Enter filename" disabled={isLoading} />
          </div>
          <button className="export-button" onClick={handleExport} disabled={isLoading || !exportFilename.trim()}>
            {isLoading ? '⏳' : '📥 Export Data'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsChart;




