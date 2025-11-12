import { useState } from 'react';
import { useLoading } from '../contexts/LoadingContext';
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
  const [loading, setLoading] = useState(false);
  const { setLoading: setGlobalLoading } = useLoading();

  const handleExecute = async () => {
    if (!query || !query.trim()) return;
  setLoading(true);
  setGlobalLoading(true);
    setResponse(null);
    try {
      const res = await fetch(`${API_BASE}/api/nl-to-mongodb`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query }),
      });

      if (!res.ok) {
        let errText = await res.text();
        try { errText = JSON.parse(errText); } catch (e) {}
        setResponse({ data: [], error: errText });
        setLoading(false);
        return;
      }

      const data = await res.json();

      if (data.success) {
        setResponse({ data: data.data || [], error: null, raw: data });
      } else {
        setResponse({ data: [], error: data.error || 'Query failed' });
      }
    } catch (e) {
      console.error('NoSQLChatbot handleExecute error', e);
      setResponse({ data: [], error: e.message || String(e) });
    } finally {
      setLoading(false);
      setGlobalLoading(false);
    }
  };

  return (
    <div className="chat-card">
      <div className="chat-card-header">
        <div>
          <h3>NoSQL Chatbot</h3>
          <p className="muted">Query your MongoDB data using natural language</p>
        </div>
      </div>

      <div className="chat-card-body">
        <textarea
          className="chat-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="e.g. Show me all images with resolution > 4k"
          rows={4}
        />

        <div className="chat-actions">
          <button className="primary-button" onClick={handleExecute} disabled={loading || !query.trim()}>
            {loading ? 'Searching...' : 'Search'}
          </button>
          <button className="secondary-button" onClick={() => { setQuery(''); setResponse(null); }}>
            Clear
          </button>
        </div>

        <div className="response-area">
          {response?.error && <div className="callout error">{typeof response.error === 'string' ? response.error : JSON.stringify(response.error)}</div>}
          {response?.raw?.answer && <div className="callout">{response.raw.answer}</div>}

          {response && response.data && response.data.length > 0 && (
            <div className="results">
              <div className="results-count">Showing {response.data.length} document{response.data.length !== 1 ? 's' : ''}</div>
              {(() => {
                const firstDoc = response.data[0];
                if (firstDoc && typeof firstDoc === 'object') {
                  const columns = Object.keys(firstDoc);
                  return (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>{columns.map((col, i) => <th key={i}>{col}</th>)}</tr>
                        </thead>
                        <tbody>
                          {response.data.map((doc, i) => (
                            <tr key={i}>{columns.map((col, j) => (
                              <td key={j}>{doc[col] === null || doc[col] === undefined ? <span className="null">NULL</span> : (typeof doc[col] === 'object' ? <pre>{JSON.stringify(doc[col], null, 2)}</pre> : String(doc[col]))}</td>
                            ))}</tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                }
                return <pre>{JSON.stringify(response.data, null, 2)}</pre>;
              })()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default NoSQLChatbot;