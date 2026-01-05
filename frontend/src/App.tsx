import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import HomePage from './pages/HomePage';
import SessionHistoryPage from './pages/SessionHistoryPage';
import TopicCoveragePage from './pages/TopicCoveragePage';
import AuthForm from './components/AuthForm';
import ThemeToggle from './components/ThemeToggle';
import './App.css';
import './themes.css';

const AppContent: React.FC = () => {
  const { authState, logout, error, clearError } = useAuth();
  const location = useLocation();

  const handleAuthSuccess = () => {
    clearError();
  };

  const handleAuthError = (errorMessage: string) => {
    console.error('Auth error:', errorMessage);
  };

  const handleLogout = () => {
    logout();
  };

  if (!authState.isAuthenticated) {
    return (
      <div className="App">
        <header className="App-header">
          <div className="header-content">
            <h1 className="app-title">GCSE Question Generator</h1>
            <p className="app-subtitle">
              Generate high-quality GCSE exam questions using AI
            </p>
          </div>
        </header>
        
        <main className="App-main">
          {error && (
            <div className="error-message">
              {error}
              <button onClick={clearError} className="error-dismiss">×</button>
            </div>
          )}
          <AuthForm 
            onAuthSuccess={handleAuthSuccess}
            onError={handleAuthError}
          />
        </main>
        
        <footer className="App-footer">
          <p>&copy; 2024 GCSE Question Generator. Powered by AWS Bedrock.</p>
        </footer>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <Link to="/" className="app-title-link">
            <h1 className="app-title">GCSE Question Generator</h1>
          </Link>
          <nav className="main-nav">
            <Link 
              to="/" 
              className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
            >
              Generator
            </Link>
            <Link 
              to="/history" 
              className={`nav-link ${location.pathname === '/history' ? 'active' : ''}`}
            >
              History
            </Link>
            <Link 
              to="/coverage" 
              className={`nav-link ${location.pathname === '/coverage' ? 'active' : ''}`}
            >
              Coverage
            </Link>
          </nav>
          <div className="user-info">
            <ThemeToggle />
            <span>Welcome, {authState.user?.username}!</span>
            <button onClick={handleLogout} className="logout-btn">
              Logout
            </button>
          </div>
        </div>
      </header>
      
      <main className="App-main">
        {error && (
          <div className="error-message">
            {error}
            <button onClick={clearError} className="error-dismiss">×</button>
          </div>
        )}
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/history" element={<SessionHistoryPage />} />
          <Route path="/coverage" element={<TopicCoveragePage />} />
        </Routes>
      </main>
      
      <footer className="App-footer">
        <p>&copy; 2024 GCSE Question Generator. Powered by AWS Bedrock.</p>
      </footer>
    </div>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <AppContent />
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;