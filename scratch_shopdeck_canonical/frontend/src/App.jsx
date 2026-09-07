import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './screens/Dashboard';
import NDR from './screens/NDR';
import Orders from './screens/Orders';
import Customers from './screens/Customers';
import Events from './screens/Events';
import SyncHealth from './screens/SyncHealth';
import { AuthProvider, useAuth } from './shopdeck-auth';

function AccessDenied() {
  const { user, logout } = useAuth();
  return (
    <div style={{ padding: '40px', textAlign: 'center' }}>
      <h2>Access Denied</h2>
      <p>Hello {user.name}, you are logged in but do not have the required <strong>SHOPDECK_VIEW</strong> permission to access this application.</p>
      <button onClick={logout} style={{ padding: '10px 20px', cursor: 'pointer' }}>Sign Out</button>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, hasPermission } = useAuth();

  if (!isAuthenticated) {
    const loginUrl = (window.AARAM_CONFIG?.IDENTITY_URL || import.meta.env.VITE_IDENTITY_URL || "http://127.0.0.1:5174").replace(/\/$/, "");
    const currentUrl = encodeURIComponent(window.location.href);
    window.location.href = `${loginUrl}/login?redirect=${currentUrl}`;
    return <p>Redirecting to login...</p>;
  }

  if (!hasPermission('SHOPDECK_VIEW')) {
    return <AccessDenied />;
  }

  return children;
}

function AppLayout({ apiBaseUrl }) {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <Router>
      <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'sans-serif' }}>
        <nav style={{ width: '200px', backgroundColor: '#f4f4f4', padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div>
            <h2>ShopDeck</h2>
            <ul style={{ listStyleType: 'none', padding: 0 }}>
              <li><Link to="/">Dashboard</Link></li>
              <li><Link to="/ndr">NDR</Link></li>
              <li><Link to="/orders">Orders</Link></li>
              <li><Link to="/customers">Customers</Link></li>
              <li><Link to="/events">Events</Link></li>
              <li><Link to="/sync-health">Sync Health</Link></li>
            </ul>
          </div>
          
          {isAuthenticated && (
            <div style={{ marginTop: 'auto', borderTop: '1px solid #ddd', paddingTop: '15px' }}>
              <p style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#555' }}>
                Logged in as:<br/>
                <strong style={{ color: '#000' }}>{user.name}</strong>
              </p>
              <button 
                onClick={logout} 
                style={{ padding: '8px 12px', cursor: 'pointer', width: '100%', backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '4px' }}
              >
                Sign Out
              </button>
            </div>
          )}
        </nav>
        
        <main style={{ flex: 1, padding: '20px' }}>
          <Routes>
            <Route path="/" element={<ProtectedRoute><Dashboard apiBaseUrl={apiBaseUrl} /></ProtectedRoute>} />
            <Route path="/ndr" element={<ProtectedRoute><NDR apiBaseUrl={apiBaseUrl} /></ProtectedRoute>} />
            <Route path="/orders" element={<ProtectedRoute><Orders apiBaseUrl={apiBaseUrl} /></ProtectedRoute>} />
            <Route path="/customers" element={<ProtectedRoute><Customers apiBaseUrl={apiBaseUrl} /></ProtectedRoute>} />
            <Route path="/events" element={<ProtectedRoute><Events apiBaseUrl={apiBaseUrl} /></ProtectedRoute>} />
            <Route path="/sync-health" element={<ProtectedRoute><SyncHealth apiBaseUrl={apiBaseUrl} /></ProtectedRoute>} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function App() {
  const apiBaseUrl = window.AARAM_CONFIG?.API_URL || import.meta.env.VITE_API_URL || "http://127.0.0.1:8200/api/v1";

  return (
    <AuthProvider>
      <AppLayout apiBaseUrl={apiBaseUrl} />
    </AuthProvider>
  );
}

export default App;
