import { Link, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import './App.css';
import MasterChatbot from './components/MasterChatbot';
import NoSQLChatbot from './components/NoSQLChatbot';
import SQLChatbot from './components/SQLChatbot';
import Sidebar from './components/Sidebar';
import { useEffect, useState } from 'react';
import { LoadingProvider } from './contexts/LoadingContext';
import LoaderOverlay from './components/LoaderOverlay';

function App() {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light');

  return (
    <Router>
      <LoadingProvider>
        <div className="app-shell">
          <Sidebar onThemeToggle={toggleTheme} currentTheme={theme} />
          <main className="main-content">
            <Routes>
              <Route path="/master" element={<MasterChatbot />} />
              <Route path="/sql" element={<SQLChatbot />} />
              <Route path="/nosql" element={<NoSQLChatbot />} />
              <Route path="/" element={<MasterChatbot />} />
            </Routes>
          </main>
          <LoaderOverlay />
        </div>
      </LoadingProvider>
    </Router>
  );
}

export default App;