import { Link, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import './App.css';
import MasterChatbot from './components/MasterChatbot';
import NoSQLChatbot from './components/NoSQLChatbot';
import SQLChatbot from './components/SQLChatbot';

function App() {
  return (
    <Router>
      <nav className="navbar">
        <Link to="/master">Master (AI Chatbot)</Link>
        <Link to="/sql">SQL Chatbot</Link>
        <Link to="/nosql">NoSQL Chatbot</Link>
      </nav>
      <div className="main-content">
        <Routes>
          <Route path="/master" element={<MasterChatbot />} />
          <Route path="/sql" element={<SQLChatbot />} />
          <Route path="/nosql" element={<NoSQLChatbot />} />
          <Route path="/" element={<MasterChatbot />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;