import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../services/apiClient';
import { SessionSummary, SessionHistoryResponse, SessionStatistics } from '../types/api';
import './SessionHistoryPage.css';

const SessionHistoryPage: React.FC = () => {
  const { authState } = useAuth();
  const navigate = useNavigate();
  
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [statistics, setStatistics] = useState<SessionStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [lastEvaluatedKey, setLastEvaluatedKey] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<string>('');

  useEffect(() => {
    if (!authState.isAuthenticated) {
      navigate('/');
      return;
    }
    
    loadSessionHistory();
    loadStatistics();
  }, [authState.isAuthenticated, navigate]);

  const loadSessionHistory = async (reset: boolean = true) => {
    try {
      setLoading(true);
      setError(null);
      
      const response: SessionHistoryResponse = await apiClient.getSessionHistory(
        50, 
        reset ? null : lastEvaluatedKey
      );
      
      if (reset) {
        setSessions(response.sessions);
      } else {
        setSessions(prev => [...prev, ...response.sessions]);
      }
      
      setHasMore(response.has_more);
      setLastEvaluatedKey(response.last_evaluated_key);
      
    } catch (err: any) {
      console.error('Failed to load session history:', err);
      setError(err.error?.message || 'Failed to load session history');
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const stats = await apiClient.getSessionStatistics();
      setStatistics(stats);
    } catch (err: any) {
      console.error('Failed to load statistics:', err);
      // Don't show error for statistics as it's not critical
    }
  };

  const loadMoreSessions = () => {
    if (hasMore && !loading) {
      loadSessionHistory(false);
    }
  };

  const handleSessionClick = (sessionId: string) => {
    navigate(`/session/${sessionId}`);
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 1) {
      return `${Math.round(seconds * 1000)}ms`;
    }
    return `${seconds.toFixed(1)}s`;
  };

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = searchQuery === '' || 
      session.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.metadata.topic.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesTopic = selectedTopic === '' || session.metadata.topic === selectedTopic;
    
    return matchesSearch && matchesTopic;
  });

  const uniqueTopics = Array.from(new Set(sessions.map(s => s.metadata.topic))).sort();

  if (!authState.isAuthenticated) {
    return null;
  }

  return (
    <div className="session-history-page">
      <div className="session-history-header">
        <h1>Session History</h1>
        <button 
          className="back-button"
          onClick={() => navigate('/')}
        >
          ← Back to Generator
        </button>
      </div>

      {statistics && (
        <div className="statistics-section">
          <h2>Your Statistics</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{statistics.total_sessions}</div>
              <div className="stat-label">Total Sessions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{statistics.recent_sessions_7_days}</div>
              <div className="stat-label">Recent Sessions (7 days)</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{statistics.total_questions_generated}</div>
              <div className="stat-label">Questions Generated</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{statistics.average_questions_per_session.toFixed(1)}</div>
              <div className="stat-label">Avg Questions/Session</div>
            </div>
          </div>
          
          {statistics.most_common_topics.length > 0 && (
            <div className="common-topics">
              <h3>Most Common Topics</h3>
              <div className="topic-list">
                {statistics.most_common_topics.map((topic, index) => (
                  <div key={index} className="topic-item">
                    <span className="topic-name">{topic.topic}</span>
                    <span className="topic-count">{topic.count} sessions</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="filters-section">
        <div className="search-filter">
          <input
            type="text"
            placeholder="Search sessions by query or topic..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="topic-filter">
          <select
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
            className="topic-select"
          >
            <option value="">All Topics</option>
            {uniqueTopics.map(topic => (
              <option key={topic} value={topic}>{topic}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="sessions-section">
        <h2>Your Sessions ({filteredSessions?.length || 0})</h2>
        
        {loading && (sessions?.length || 0) === 0 ? (
          <div className="loading">Loading session history...</div>
        ) : error ? (
          <div className="error">
            <p>{error}</p>
            <button onClick={() => loadSessionHistory()}>Try Again</button>
          </div>
        ) : (filteredSessions?.length || 0) === 0 ? (
          <div className="no-sessions">
            {(sessions?.length || 0) === 0 ? (
              <p>You haven't generated any questions yet. <a href="/">Start generating questions</a> to see your history here.</p>
            ) : (
              <p>No sessions match your search criteria.</p>
            )}
          </div>
        ) : (
          <>
            <div className="sessions-list">
              {filteredSessions.map((session) => (
                <div
                  key={session.session_id}
                  className="session-card"
                  onClick={() => handleSessionClick(session.session_id)}
                >
                  <div className="session-header">
                    <div className="session-query">{session.query}</div>
                    <div className="session-date">{formatDate(session.timestamp)}</div>
                  </div>
                  
                  <div className="session-details">
                    <div className="session-meta">
                      <span className="topic-badge">{session.metadata.topic}</span>
                      <span className={`tier-badge tier-${session.metadata.tier.toLowerCase()}`}>
                        {session.metadata.tier}
                      </span>
                      <span className="question-count">{session.question_count} questions</span>
                      <span className="total-marks">{session.metadata.total_marks} marks</span>
                    </div>
                    
                    <div className="session-stats">
                      <span className="generation-time">
                        Generated in {formatDuration(session.metadata.generation_time || 0)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {hasMore && (
              <div className="load-more-section">
                <button
                  onClick={loadMoreSessions}
                  disabled={loading}
                  className="load-more-button"
                >
                  {loading ? 'Loading...' : 'Load More Sessions'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default SessionHistoryPage;