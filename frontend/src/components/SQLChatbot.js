import { useState } from 'react';
import './SQLChatbot.css';

// API base detection: use REACT_APP_API_URL or fallback to localhost backend in dev
const API_BASE = (() => {
  const fromEnv = (process.env.REACT_APP_API_URL || '').replace(/\/+$/, '');
  if (fromEnv) return fromEnv;
  const isLocalhost = typeof window !== 'undefined' && /localhost|127\.0\.0\.1/.test(window.location.hostname);
  return isLocalhost ? 'http://localhost:5001' : '';
})();

function SQLChatbot() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);

  const handleExecute = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/nl-to-sql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query, db_type: 'sql' }),
      });

      if (!res.ok) {
        // Try to parse JSON error, otherwise text
        let errText = await res.text();
        try { errText = JSON.parse(errText); } catch (e) {}
        setResponse({ columns: [], rows: [], error: errText });
        return;
      }

      const data = await res.json();
      console.log('Backend response:', data); // Debug log

      // backend returns { success, data, answer, summary } where data is the rows
      if (data.success) {
        // Get rows from the data field
        let rows = Array.isArray(data.data) ? data.data : [];
        console.log('Initial rows:', rows); // Debug log
        
        let columns = [];
        
        if (rows.length > 0) {
          // Handle objects: get column names from the first row
          if (!Array.isArray(rows[0]) && typeof rows[0] === 'object') {
            columns = Object.keys(rows[0]);
          }
          // Handle arrays: generate column names
          else if (Array.isArray(rows[0])) {
            columns = rows[0].map((_, i) => `Column ${i+1}`);
          }
          // Handle unexpected row format
          else {
            console.warn('Unexpected row format:', rows[0]);
            rows = [];
            columns = [];
          }
        }
        
        console.log('Processed rows:', rows); // Debug log
        console.log('Columns:', columns); // Debug log
        
        setResponse({ 
          columns, 
          rows,
          error: null,
          raw: data
        });
      } else {
        setResponse({ columns: [], rows: [], error: data.error || 'Query failed' });
      }
    } catch (e) {
      console.error('SQLChatbot handleExecute error', e);
      setResponse({ columns: [], rows: [], error: e.message || String(e) });
    }
  };

  return (
    <div>
      <h2>SQL Chatbot</h2>
      <textarea
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Ask a question about your data (e.g. 'Show me all books')"
        rows={4}
        cols={60}
      />
      <br />
      <button onClick={handleExecute}>Execute</button>
      <div>
        {/* Show API response message or error */}
        {response?.error ? (
          <div style={{color:'red', marginTop: '1rem'}}>
            {typeof response.error === 'string' ? response.error : JSON.stringify(response.error)}
          </div>
        ) : (
          response?.raw?.answer && (
            <div style={{marginTop: '1rem', fontSize: '1.1em', color: '#2c3e50'}}>
              {response.raw.answer}
            </div>
          )
        )}
        
        {/* Show results table if we have valid data */}
        {response && Array.isArray(response.rows) && (
          <div className="results">
            {/* Results count */}
            <div className="results-count">
              {response.rows.length === 0 ? (
                'No results found'
              ) : (
                `Showing ${response.rows.length} record${response.rows.length !== 1 ? 's' : ''}`
              )}
            </div>

            {/* Results table (only show if we have rows) */}
            {response.rows.length > 0 && (
              <table>
                <thead>
                  <tr>
                    {(response.columns || []).map((col, i) => (
                      <th key={i}>{col || `Column ${i+1}`}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {response.rows.map((row, i) => (
                    <tr key={i}>
                      {response.columns.map((col, j) => {
                        const value = row[col];
                        const isNumber = !isNaN(value) && value !== '';
                        const isPrice = col.toLowerCase() === 'price';
                        
                        return (
                          <td key={j} 
                              data-is-number={isNumber} 
                              data-is-price={isPrice}>
                            {value === null || value === undefined ? (
                              <span className="null">NULL</span>
                            ) : typeof value === 'object' ? (
                              JSON.stringify(value)
                            ) : isPrice ? (
                              Number(value).toLocaleString('en-IN', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                              })
                            ) : (
                              String(value)
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default SQLChatbot;