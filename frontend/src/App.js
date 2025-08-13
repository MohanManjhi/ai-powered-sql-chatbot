import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [cacheStats, setCacheStats] = useState(null);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  const formatCellValue = (value) => {
    if (value === null || value === undefined) {
      return '-';
    }
    
    // Handle date objects and date strings
    if (value instanceof Date) {
      return value.toLocaleDateString();
    }
    
    if (typeof value === 'string') {
      // Try to parse as date
      const date = new Date(value);
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString();
      }
      // Handle GMT date strings
      if (value.includes('GMT')) {
        const cleanDate = new Date(value);
        return cleanDate.toLocaleDateString();
      }
    }
    
    // Handle numbers
    if (typeof value === 'number') {
      if (Number.isInteger(value)) {
        return value.toLocaleString();
      } else {
        return value.toFixed(2);
      }
    }
    
    // Handle booleans
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

  // Fetch cache stats on component mount
  useEffect(() => {
    const fetchCacheStats = async () => {
      try {
        const response = await fetch('http://localhost:5001/api/cache/stats');
        const data = await response.json();
        if (data.success) {
          setCacheStats(data.cache_stats);
        }
      } catch (error) {
        console.log('Could not fetch cache stats');
      }
    };
    
    fetchCacheStats();
    // Refresh cache stats every 30 seconds
    const interval = setInterval(fetchCacheStats, 30000);
    
    // Security note
    console.log('🔒 Security: SQL queries are not exposed to the frontend for data protection');
    
    return () => clearInterval(interval);
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

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('http://localhost:5001/api/nl-to-sql', {
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
          sender: 'bot',
          timestamp: new Date().toLocaleTimeString()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        // Handle different types of errors
        let errorMessage;
        
        if (data.type === 'query_help') {
          // This is a helpful error with suggestions
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
          // Regular error
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
        // Request was cancelled, don't show error
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
        <div className="chat-header">
          <h1>🤖 AI SQL Chatbot</h1>
          <p>Ask questions about your database in natural language</p>
          {cacheStats && (
            <div className="cache-stats">
              <small>
                🚀 Cache: {cacheStats.active_entries} active entries
                {cacheStats.total_entries > 0 && (
                  <span> ({cacheStats.expired_entries} expired)</span>
                )}
              </small>
            </div>
          )}
        </div>

        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <div className="welcome-icon">💬</div>
              <h3>Welcome to AI SQL Chatbot!</h3>
              <p>Try asking questions like:</p>
              <ul>
                <li>"Show me all users"</li>
                <li>"What are the total orders?"</li>
                <li>"Find users with orders above $100"</li>
              </ul>
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
                
                {/* Show original question for query help messages */}
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
                
                {/* Show data table FIRST if available */}
                {message.data && message.data.length > 0 && (
                  <div className="data-table-container">
                    <strong>📊 Results:</strong>
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
                
                {/* Show performance metrics */}
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
                
                {/* Show summary AFTER data */}
                {message.summary && (
                  <div className="message-summary-standalone">
                    <strong>📊 Summary:</strong> {message.summary}
                  </div>
                )}
                
                {/* Show suggestions */}
                {message.suggestions && (
                  <div className="message-suggestions">
                    <strong>💡 Try asking:</strong>
                    <div className="suggestion-chips">
                      {message.suggestions.map((suggestion, index) => (
                        <div key={index} className="suggestion-chip" onClick={() => setInputValue(suggestion)}>
                          {suggestion}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Show capabilities */}
                {message.capabilities && (
                  <div className="message-capabilities">
                    <strong>🔧 {message.capabilities.description}</strong>
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

export default App;
