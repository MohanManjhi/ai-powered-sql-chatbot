import { useState } from 'react';

function NoSQLChatbot() {
  const [query, setQuery] = useState('db.images.find({})');
  const [response, setResponse] = useState(null);

  const handleExecute = async () => {
    const res = await fetch('/nosql/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    setResponse(data);
  };

  return (
    <div>
      <h2>NoSQL Chatbot</h2>
      <textarea
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder='MongoDB query (e.g. db.images.find({"name": "nano"}))'
        rows={4}
        cols={60}
      />
      <br />
      <button onClick={handleExecute}>Execute</button>
      <div>
        {response && response.error && <div style={{color:'red'}}>{response.error}</div>}
        {response && response.docs && (
          <pre>{JSON.stringify(response.docs, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}

export default NoSQLChatbot;