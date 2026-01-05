import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/apiClient';
import { SessionSummary, SessionDetails, SessionStatistics } from '../types/api';
import './SessionHistory.css';

interface SessionHistoryProps {
  onSessionSelect?: (sessionDetails: SessionDetails) => void;
}

const SessionHistory: React.FC<SessionHistoryProps> = ({ onSessionSelect }) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [statistics, setStatistics] = useState<SessionStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [lastEvaluatedKey, setLastEvaluatedKey] = useState<any>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTier, setSelectedTier] = useState<string>('all');
  const [selectedTopic, setSelectedTopic] = useState<string>('all');

  useEffect(() => {
    loadSessionHistory();
    loadStatistics();
  }, []);

  const loadSessionHistory = async (reset: boolean = true) => {
    try {
      if (reset) {
        setLoading(true);
        setError(null);
      } else {
        setLoadingMore(true);
      }

      const response = await apiClient.getSessionHistory(
        50, 
        reset ? undefined : lastEvaluatedKey
      );

      if (reset) {
        setSessions(response.sessions);
      } else {
        setSessions(prev => [...prev, ...response.sessions]);
      }

      setHasMore(response.has_more);
      setLastEvaluatedKey(response.last_evaluated_key);
    } catch (err: any) {
      setError(err.error?.message || 'Failed to load session history');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const stats = await apiClient.getSessionStatistics();
      setStatistics(stats);
    } catch (err: any) {
      console.error('Failed to load statistics:', err);
    }
  };

  const handleSessionClick = async (sessionId: string) => {
    try {
      const sessionDetails = await apiClient.getSessionDetails(sessionId);
      if (onSessionSelect) {
        onSessionSelect(sessionDetails);
      }
    } catch (err: any) {
      setError(err.error?.message || 'Failed to load session details');
    }
  };

  const loadMore = () => {
    if (hasMore && !loadingMore) {
      loadSessionHistory(false);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = searchTerm === '' || 
      session.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
      session.metadata.topic.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesTier = selectedTier === 'all' || 
      session.metadata.tier.toLowerCase() === selectedTier.toLowerCase();
    
    const matchesTopic = selectedTopic === 'all' || 
      session.metadata.topic.toLowerCase() === selectedTopic.toLowerCase();
    
    return matchesSearch && matchesTier && matchesTopic;
  });

  const uniqueTopics = Array.from(new Set(sessions.map(s => s.metadata.topic)));

  if (loading) {
    return (
      <div className="session-history">
        <div className="loading">Loading session history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="session-history">
        <div className="error">
          <h3>Error Loading Sessions</h3>
          <p>{error}</p>
          <button onClick={() => loadSessionHistory()} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="session-history">
      <div className="session-history-header">
        <h2>Session History</h2>
        
        {statistics && (
          <div className="statistics">
            <div className="stat-item">
              <span className="stat-value">{statistics.total_sessions}</span>
              <span className="stat-label">Total Sessions</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{statistics.total_questions_generated}</span>
              <span className="stat-label">Questions Generated</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{statistics.recent_sessions_7_days}</span>
              <span className="stat-label">Recent (7 days)</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{statistics.average_questions_per_session.toFixed(1)}</span>
              <span className="stat-label">Avg per Session</span>
            </div>
          </div>
        )}
      </div>

      <div className="filters">
        <div className="filter-group">
          <input
            type="text"
            placeholder="Search sessions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filter-group">
          <select
            value={selectedTier}
            onChange={(e) => setSelectedTier(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Tiers</option>
            <option value="foundation">Foundation</option>
            <option value="higher">Higher</option>
          </select>
        </div>
        
        <div className="filter-group">
          <select
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Topics</option>
            {uniqueTopics.map(topic => (
              <option key={topic} value={topic}>{topic}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="sessions-list">
        {filteredSessions.length === 0 ? (
          <div className="no-sessions">
            <p>No sessions found matching your criteria.</p>
            {searchTerm || selectedTier !== 'all' || selectedTopic !== 'all' ? (
              <button 
                onClick={() => {
                  setSearchTerm('');
                  setSelectedTier('all');
                  setSelectedTopic('all');
                }}
                className="clear-filters-button"
              >
                Clear Filters
              </button>
            ) : (
              <p>Start generating questions to see your session history here.</p>
            )}
          </div>
        ) : (
          filteredSessions.map(session => (
            <div
              key={session.session_id}
              className="session-item"
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
                  <span className="question-count">
                    {session.question_count} question{session.question_count !== 1 ? 's' : ''}
                  </span>
                  <span className="marks-count">
                    {session.metadata.total_marks} mark{session.metadata.total_marks !== 1 ? 's' : ''}
                  </span>
                </div>
                
                {session.metadata.generation_time && (
                  <div className="generation-time">
                    Generated in {session.metadata.generation_time.toFixed(1)}s
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {hasMore && (
        <div className="load-more">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="load-more-button"
          >
            {loadingMore ? 'Loading...' : 'Load More Sessions'}
          </button>
        </div>
      )}
    </div>
  );
};

export default SessionHistory;