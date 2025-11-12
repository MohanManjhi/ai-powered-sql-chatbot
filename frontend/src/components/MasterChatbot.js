import { useEffect, useRef, useState } from 'react';
import '../App.css';
import AnalyticsChart from './AnalyticsChart';

function MasterChatbot() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [currentAnalyticsData, setCurrentAnalyticsData] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [currentSql, setCurrentSql] = useState('');
  const [currentChartType, setCurrentChartType] = useState('auto');
  const [schemaOverview, setSchemaOverview] = useState(null);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  const API_BASE = (() => {
    const fromEnv = (process.env.REACT_APP_API_URL || '').replace(/\/+$/, '');
    if (fromEnv) return fromEnv;
    const isLocalhost = typeof window !== 'undefined' && /localhost|127\.0\.0\.1/.test(window.location.hostname);
    return isLocalhost ? 'http://localhost:5001' : '';
  })();

  const formatCellValue = (value) => {
    if (value === null || value === undefined) {
      return '-';
    }
    if (value instanceof Date) {
      return value.toLocaleDateString();
    }
    if (typeof value === 'string') {
      const date = new Date(value);
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString();
      }
      if (value.includes('GMT')) {
        const cleanDate = new Date(value);
        return cleanDate.toLocaleDateString();
      }
    }
    if (typeof value === 'number') {
      if (Number.isInteger(value)) {
        return value.toLocaleString();
      } else {
        return value.toFixed(2);
      }
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    return String(value);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    console.log('🔒 Security: SQL queries are not exposed to the frontend for data protection');
  }, []);

  useEffect(() => {
    const fetchSchema = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/schema`);
        const json = await res.json();
        if (json.success && json.schema) {
          const tables = Object.keys(json.schema);
          setSchemaOverview({
            tableCount: tables.length,
            tables: tables.slice(0, 8),
          });
        }
      } catch (e) {
        // ignore
      }
    };
    fetchSchema();
  }, []);

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
      setIsGenerating(false);
      const stopMessage = {
        id: Date.now() + 1,
        text: "Generation stopped by user.",
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString(),
        isStopped: true
      };
      setMessages(prev => [...prev, stopMessage]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setIsGenerating(true);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_BASE}/api/nl-to-sql`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: inputValue }),
        signal: abortControllerRef.current.signal
      });

      const data = await response.json();

      if (data.success) {
        const botMessage = {
          id: Date.now() + 1,
          text: data.answer,
          summary: data.summary,
          suggestions: data.suggestions,
          capabilities: data.capabilities,
          data: data.data,
          chart_request: data.chart_request,
          sender: 'bot',
          timestamp: new Date().toLocaleTimeString()
        };
        setMessages(prev => [...prev, botMessage]);
        if (data.data && data.data.length > 0) {
          const requestedChartType = data.chart_request?.requested ? (data.chart_request.type || 'auto') : null;
          setCurrentAnalyticsData(data.data);
          setCurrentQuestion(inputValue);
          setCurrentSql('');
          if (requestedChartType) {
            setCurrentChartType(requestedChartType);
            setShowAnalytics(true);
          }
        }
      } else {
        let errorMessage;
        if (data.type === 'query_help') {
          errorMessage = {
            id: Date.now() + 1,
            text: data.error,
            suggestions: data.suggestions,
            originalQuestion: data.original_question,
            sender: 'bot',
            timestamp: new Date().toLocaleTimeString(),
            isQueryHelp: true
          };
        } else {
          errorMessage = {
            id: Date.now() + 1,
            text: `Error: ${data.error}`,
            sender: 'bot',
            timestamp: new Date().toLocaleTimeString(),
            isError: true
          };
        }
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        return;
      }
      const errorMessage = {
        id: Date.now() + 1,
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  return (
    <div className="App">
      <div className="chat-container">
        <div className="chat-header master-hero">
          <div className="hero-left">
            <h1>AI Database Assistant</h1>
            <p>Ask natural-language questions about any connected database (SQL or MongoDB). I'll find the data and explain the results in plain language.</p>
          </div>
          <div className="hero-right">
            <div className="hero-badge">Unified DB • SQL + NoSQL</div>
          </div>
        </div>

        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <div className="welcome-icon">💬</div>
              <h3>Welcome to your Database Assistant!</h3>
              <p>
                This assistant works across your connected SQL and NoSQL databases. You don't need to know table or collection names — just ask in plain language (for example, “show monthly sales” or “top customers by revenue”), and I'll locate the data and explain it.
              </p>
              {schemaOverview && (
                <div className="message-summary" style={{ textAlign: 'left' }}>
                  <span className="summary-text">
                    Connected database has {schemaOverview.tableCount} tables.
                  </span>
                </div>
              )}
              <div className="welcome-suggestions">
                {(schemaOverview?.tables || []).slice(0,4).map((t) => (
                  <div key={t} className="suggestion-chip" onClick={() => setInputValue(`Show me ${t}`)}>
                    Show {t}
                  </div>
                ))}
                <div className="suggestion-chip" onClick={() => setInputValue("Count total records")}>Count total records</div>
                <div className="suggestion-chip" onClick={() => setInputValue("Show me monthly totals and a line chart")}>Monthly line chart</div>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.sender} ${message.isError ? 'error' : ''} ${message.isStopped ? 'stopped' : ''} ${message.isQueryHelp ? 'query-help' : ''}`}
            >
              <div className="message-avatar">
                {message.sender === 'user' ? 'U' : 'A'}
              </div>
              <div className="message-content">
                <div className="message-text">{message.text}</div>
                {message.isQueryHelp && message.originalQuestion && (
                  <div className="original-question">
                    <strong>Your question:</strong> "{message.originalQuestion}"
                    <button 
                      className="retry-button"
                      onClick={() => setInputValue(message.originalQuestion)}
                    >
                      🔄 Try Again
                    </button>
                  </div>
                )}
                {message.data && message.data.length > 0 && (
                  <div className="data-table-container">
                    <div className="data-table-header">
                      <span className="results-label">📊 Results ({message.data.length} rows)</span>
                    </div>
                    <div className="data-table">
                      <table>
                        <thead>
                          <tr>
                            {Object.keys(message.data[0]).map((key) => (
                              <th key={key}>{key.replace(/_/g, ' ').toUpperCase()}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {message.data.map((row, index) => (
                            <tr key={index}>
                              {Object.values(row).map((value, cellIndex) => (
                                <td key={cellIndex}>
                                  {formatCellValue(value)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                {message.performance && (
                  <div className="performance-metrics">
                    <small>
                      ⚡ Response time: {message.performance.total_time}s
                      {message.performance.cached !== 'none' && (
                        <span className="cache-indicator"> 🚀 Cached</span>
                      )}
                    </small>
                  </div>
                )}
                {message.summary && (
                  <div className="message-summary">
                    <span className="summary-text">{message.summary}</span>
                  </div>
                )}
                {/* removed Create Chart / Download action buttons from Master UI to keep it focused and standalone */}
                {message.suggestions && (
                  <div className="message-suggestions">
                    <div className="suggestion-chips">
                      {message.suggestions.map((suggestion, index) => (
                        <div key={index} className="suggestion-chip" onClick={() => setInputValue(suggestion)}>
                          {suggestion}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {message.capabilities && (
                  <div className="message-capabilities">
                    <div className="capabilities-list">
                      {message.capabilities.features.map((feature, index) => (
                        <div key={index} className="capability-item">
                          {feature}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="message-timestamp">{message.timestamp}</div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="message bot">
              <div className="message-avatar">A</div>
              <div className="message-content">
                <div className="loading-indicator">
                  <div className="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <div className="loading-text">Generating response...</div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {showAnalytics && currentAnalyticsData && (
          <div className="data-table-container">
            <div className="data-table-header">
              <span className="results-label">📈 Analytics</span>
            </div>
            <div style={{ padding: '16px' }}>
              <AnalyticsChart
                data={currentAnalyticsData}
                question={currentQuestion}
                sql={currentSql}
                initialChartType={currentChartType}
              />
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-container">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your database..."
              disabled={isLoading}
              rows="1"
            />
            <div className="button-group">
              {isGenerating && (
                <button 
                  type="button"
                  onClick={stopGeneration}
                  className="stop-button"
                  title="Stop generation"
                >
                  ⏹️
                </button>
              )}
              <button 
                type="submit" 
                disabled={!inputValue.trim() || isLoading}
                className="send-button"
              >
                {isLoading ? '⏳' : 'Send'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default MasterChatbot;