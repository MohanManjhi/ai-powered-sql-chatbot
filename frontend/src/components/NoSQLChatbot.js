import { useState } from 'react';
import './NoSQLChatbot.css';

// API base detection: use REACT_APP_API_URL or fallback to localhost backend in dev
const API_BASE = (() => {
  const fromEnv = (process.env.REACT_APP_API_URL || '').replace(/\/+$/, '');
  if (fromEnv) return fromEnv;
  const isLocalhost = typeof window !== 'undefined' && /localhost|127\.0\.0\.1/.test(window.location.hostname);
  return isLocalhost ? 'http://localhost:5001' : '';
})();

function NoSQLChatbot() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);

  const handleExecute = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/nl-to-mongodb`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question: query
        }),
      });

      if (!res.ok) {
        let errText = await res.text();
        try { errText = JSON.parse(errText); } catch (e) {}
        setResponse({ data: [], error: errText });
        return;
      }

      const data = await res.json();
      console.log('Backend response:', data); // Debug log

      if (data.success) {
        setResponse({
          data: data.data || [],
          error: null,
          raw: data
        });
      } else {
        setResponse({ data: [], error: data.error || 'Query failed' });
      }
    } catch (e) {
      console.error('NoSQLChatbot handleExecute error', e);
      setResponse({ data: [], error: e.message || String(e) });
    }
  };

  return (
    <div>
      <h2>NoSQL Chatbot</h2>
      <textarea
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Ask questions about your MongoDB data (e.g., 'Show me all photos in photodb', 'Find photos with high resolution')"
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
        
        {/* Show results if we have data */}
        {response && response.data && response.data.length > 0 && (
          <div className="results">
            {/* Results count */}
            <div className="results-count">
              Showing {response.data.length} document{response.data.length !== 1 ? 's' : ''}
            </div>

            {/* Results in a formatted table if possible */}
            {(() => {
              const firstDoc = response.data[0];
              if (firstDoc && typeof firstDoc === 'object') {
                const columns = Object.keys(firstDoc);
                return (
                  <table>
                    <thead>
                      <tr>
                        {columns.map((col, i) => (
                          <th key={i}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {response.data.map((doc, i) => (
                        <tr key={i}>
                          {columns.map((col, j) => (
                            <td key={j}>
                              {doc[col] === null || doc[col] === undefined ? (
                                <span className="null">NULL</span>
                              ) : typeof doc[col] === 'object' ? (
                                <pre>{JSON.stringify(doc[col], null, 2)}</pre>
                              ) : (
                                String(doc[col])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                );
              } else {
                // Fallback to JSON view if data is not tabular
                return <pre>{JSON.stringify(response.data, null, 2)}</pre>;
              }
            })()}
          </div>
        )}
      </div>
    </div>
  );
}

export default NoSQLChatbot;