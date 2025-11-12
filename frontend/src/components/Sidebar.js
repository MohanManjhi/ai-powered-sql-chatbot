import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import '../App.css';
import './Sidebar.css';

const Icon = ({ name }) => {
  // Minimal inline SVGs for a light, modern look
  if (name === 'assistant') return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <rect x="2" y="3" width="20" height="14" rx="2" fill="currentColor" opacity="0.08" />
      <path d="M7 8h10M7 12h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
  if (name === 'sql') return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <circle cx="12" cy="8" r="3" stroke="currentColor" strokeWidth="1.6" />
      <rect x="6" y="12" width="12" height="6" rx="1" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
  if (name === 'nosql') return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path d="M4 7c4-3 8-3 12 0v10c-4 3-8 3-12 0V7z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="11" r="1.6" fill="currentColor" />
    </svg>
  );
  if (name === 'settings') return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path d="M12 15.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06A2 2 0 113.28 16.9l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82L4.31 3.28A2 2 0 116.9 3.28l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09c0 .58.37 1.09.94 1.34.57.25 1.24.14 1.7-.27l.06-.06A2 2 0 1120.72 7.1l-.06.06a1.65 1.65 0 00-.33 1.82V9c0 .58-.37 1.09-.94 1.34-.57.25-1.24.14-1.7-.27l-.06-.06A1.65 1.65 0 0013 9.91V12z" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" opacity="0.9" />
    </svg>
  );
  return null;
};

function Sidebar({ onThemeToggle, currentTheme }) {
  const [showSettings, setShowSettings] = useState(false);
  const [dbCounts, setDbCounts] = useState({ sql: 0, nosql: 0 });
  const [loading, setLoading] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    // refresh counts when settings opens
    if (showSettings) fetchCounts();
  }, [showSettings]);

  useEffect(() => {
    // close mobile sidebar on route change
    setMobileOpen(false);
  }, [location.pathname]);

  const fetchCounts = async () => {
    setLoading(true);
    try {
      const res = await fetch((process.env.REACT_APP_API_URL || '') + '/api/health-details');
      const json = await res.json();
      if (json && json.success) {
        const sql = json.sql ? Object.values(json.sql).filter(s => s.ok).length : 0;
        const nosql = json.mongo && json.mongo.ok ? 1 : 0;
        setDbCounts({ sql, nosql });
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* floating mobile toggle shown when sidebar is closed on small screens */}
      {!mobileOpen && <button className="mobile-toggle" aria-label="Open menu" onClick={() => setMobileOpen(true)}>☰</button>}
      <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`} aria-hidden={!mobileOpen && window.innerWidth < 900}>
      <div className="sidebar-header">
        <button className="hamburger" aria-label={mobileOpen ? 'Close menu' : 'Open menu'} onClick={() => setMobileOpen(o => !o)}>
          {mobileOpen ? '✕' : '☰'}
        </button>
        <div className="logo">🧠</div>
        <div className="app-title">
          <div className="title">Assistant</div>
          <div className="subtitle">AI Database</div>
        </div>
      </div>

      <nav className="side-nav">
        <Link className="side-link" to="/master" onClick={() => setMobileOpen(false)}><Icon name="assistant" /> <span>Assistant</span></Link>
        <Link className="side-link" to="/sql" onClick={() => setMobileOpen(false)}><Icon name="sql" /> <span>SQL</span></Link>
        <Link className="side-link" to="/nosql" onClick={() => setMobileOpen(false)}><Icon name="nosql" /> <span>NoSQL</span></Link>
      </nav>

      <div className="sidebar-footer">
        <button className="theme-toggle" onClick={onThemeToggle} aria-label="Toggle theme">
          {currentTheme === 'light' ? '🌙' : '☀️'}
        </button>
        <button className="settings-button" onClick={() => setShowSettings(true)} aria-haspopup="dialog">
          <Icon name="settings" />
        </button>
      </div>

      {showSettings && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Settings dialog">
          <div className="modal-card">
            <div className="settings-card">
              <div className="settings-header">
                <strong>Settings</strong>
                <button onClick={() => setShowSettings(false)} className="close-btn" aria-label="Close settings">✕</button>
              </div>
              <div className="settings-body">
                <div className="setting-item">
                  <div className="setting-title">Connected SQL databases</div>
                  <div className="setting-value">{loading ? 'Checking...' : `${dbCounts.sql} database${dbCounts.sql !== 1 ? 's' : ''} connected`}</div>
                </div>
                <div className="setting-item">
                  <div className="setting-title">Connected NoSQL databases</div>
                  <div className="setting-value">{loading ? 'Checking...' : `${dbCounts.nosql} ${dbCounts.nosql === 1 ? 'database' : 'databases'} connected`}</div>
                </div>
                <div style={{ marginTop: 12 }}>
                  <button className="refresh-btn" onClick={fetchCounts}>Refresh</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      </aside>
      {/* mobile backdrop: covers the screen when sidebar is open on small devices */}
      {mobileOpen && <div className="mobile-backdrop" onClick={() => setMobileOpen(false)} aria-hidden="true" />}
      </>
  );
}

export default Sidebar;
