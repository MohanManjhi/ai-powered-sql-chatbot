import { useState } from 'react';

function SQLChatbot() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);

  const handleExecute = async () => {
    const res = await fetch('/sql/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    setResponse(data);
  };

  return (
    <div>
      <h2>SQL Chatbot</h2>
      <textarea
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Write your SQL query here..."
        rows={4}
        cols={60}
      />
      <br />
      <button onClick={handleExecute}>Execute</button>
      <div>
        {response && response.error && <div style={{color:'red'}}>{response.error}</div>}
        {response && response.columns && response.rows && (
          <table>
            <thead>
              <tr>
                {response.columns.map(col => <th key={col}>{col}</th>)}
              </tr>
            </thead>
            <tbody>
              {response.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => <td key={j}>{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default SQLChatbot;