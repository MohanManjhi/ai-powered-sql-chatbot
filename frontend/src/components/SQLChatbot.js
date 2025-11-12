import { useState } from 'react';
import { useLoading } from '../contexts/LoadingContext';
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
  const [loading, setLoading] = useState(false);
  const { setLoading: setGlobalLoading } = useLoading();

  const handleExecute = async () => {
    if (!query || !query.trim()) return;
  setLoading(true);
  setGlobalLoading(true);
    setResponse(null);
    try {
      const res = await fetch(`${API_BASE}/api/nl-to-sql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query, db_type: 'sql' }),
      });

      if (!res.ok) {
        let errText = await res.text();
        try { errText = JSON.parse(errText); } catch (e) {}
        setResponse({ columns: [], rows: [], error: errText });
        setLoading(false);
        return;
      }

      const data = await res.json();

      if (data.success) {
        const rows = Array.isArray(data.data) ? data.data : [];
        let columns = [];
        if (rows.length > 0) {
          if (typeof rows[0] === 'object' && !Array.isArray(rows[0])) {
            columns = Object.keys(rows[0]);
          } else if (Array.isArray(rows[0])) {
            columns = rows[0].map((_, i) => `Column ${i+1}`);
          }
        }
        setResponse({ columns, rows, error: null, raw: data });
      } else {
        setResponse({ columns: [], rows: [], error: data.error || 'Query failed' });
      }
    } catch (err) {
      console.error(err);
      setResponse({ columns: [], rows: [], error: err.message || String(err) });
    } finally {
      setLoading(false);
      setGlobalLoading(false);
    }
  
  };

  return (
    <div className="chat-card">
      <div className="chat-card-header">
        <div>
          <h3>SQL Chatbot</h3>
          <p className="muted">Ask questions about your SQL databases in plain English</p>
        </div>
      </div>

      <div className="chat-card-body">
        <textarea
          className="chat-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="e.g. Show me top 10 students by year"
          rows={4}
        />

        <div className="chat-actions">
          <button className="primary-button" onClick={handleExecute} disabled={loading || !query.trim()}>
            {loading ? 'Running...' : 'Run Query'}
          </button>
          <button className="secondary-button" onClick={() => { setQuery(''); setResponse(null); }}>
            Clear
          </button>
        </div>

        <div className="response-area">
          {response?.error && (
            <div className="callout error">{typeof response.error === 'string' ? response.error : JSON.stringify(response.error)}</div>
          )}

          {response?.raw?.answer && (
            <div className="callout">{response.raw.answer}</div>
          )}

          {response && Array.isArray(response.rows) && (
            <div className="results">
              <div className="results-count">{response.rows.length === 0 ? 'No results found' : `Showing ${response.rows.length} records`}</div>
              {response.rows.length > 0 && (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>{(response.columns || []).map((col, i) => <th key={i}>{col || `Column ${i+1}`}</th>)}</tr>
                    </thead>
                    <tbody>
                      {response.rows.map((row, i) => (
                        <tr key={i}>
                          {response.columns.map((col, j) => (
                            <td key={j}>{row[col] === null || row[col] === undefined ? <span className="null">NULL</span> : (typeof row[col] === 'object' ? JSON.stringify(row[col]) : String(row[col]))}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SQLChatbot;