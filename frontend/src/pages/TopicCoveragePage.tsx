import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../services/apiClient';
import './TopicCoveragePage.css';

interface CoverageStats {
  [topic: string]: {
    count: number;
    subtopics: { [subtopic: string]: number };
    last_generated: string;
    percentage: number;
  };
}

interface CoverageData {
  coverage_stats: CoverageStats;
  total_questions: number;
  coverage_percentage: number;
  period_days: number;
}

interface SuggestionsData {
  suggested_topics: string[];
  suggestion_count: number;
  analysis_period_days: number;
  current_coverage: {
    total_questions: number;
    topics_covered: number;
    coverage_percentage: number;
  };
}

const TopicCoveragePage: React.FC = () => {
  const { authState } = useAuth();
  const user = authState.user;
  const sessionToken = authState.sessionToken;
  const [coverageData, setCoverageData] = useState<CoverageData | null>(null);
  const [suggestionsData, setSuggestionsData] = useState<SuggestionsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDays, setSelectedDays] = useState(30);
  const [sortBy, setSortBy] = useState<'topic' | 'count' | 'percentage' | 'last_generated'>('count');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    if (user && sessionToken) {
      fetchCoverageData();
      fetchSuggestions();
    }
  }, [user, sessionToken, selectedDays]);

  const fetchCoverageData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get(`/user/coverage?days=${selectedDays}`, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`
        }
      });
      
      setCoverageData(response.data);
    } catch (err: any) {
      console.error('Failed to fetch coverage data:', err);
      setError(err.response?.data?.error?.message || 'Failed to load coverage data');
    } finally {
      setLoading(false);
    }
  };

  const fetchSuggestions = async () => {
    try {
      const response = await apiClient.get(`/user/suggestions?days=${selectedDays}&max_suggestions=5`, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`
        }
      });
      
      setSuggestionsData(response.data);
    } catch (err: any) {
      console.error('Failed to fetch suggestions:', err);
      // Don't set error for suggestions failure - it's not critical
    }
  };

  const handleSort = (column: 'topic' | 'count' | 'percentage' | 'last_generated') => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const getSortedTopics = () => {
    if (!coverageData) return [];
    
    const topics = Object.entries(coverageData.coverage_stats);
    
    return topics.sort(([topicA, dataA], [topicB, dataB]) => {
      let valueA: any, valueB: any;
      
      switch (sortBy) {
        case 'topic':
          valueA = topicA;
          valueB = topicB;
          break;
        case 'count':
          valueA = dataA.count;
          valueB = dataB.count;
          break;
        case 'percentage':
          valueA = dataA.percentage;
          valueB = dataB.percentage;
          break;
        case 'last_generated':
          valueA = new Date(dataA.last_generated);
          valueB = new Date(dataB.last_generated);
          break;
        default:
          valueA = dataA.count;
          valueB = dataB.count;
      }
      
      if (sortOrder === 'asc') {
        return valueA > valueB ? 1 : -1;
      } else {
        return valueA < valueB ? 1 : -1;
      }
    });
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return 'Unknown';
    }
  };

  const generateCoverageHeatmap = () => {
    if (!coverageData) return null;
    
    const topics = Object.keys(coverageData.coverage_stats);
    const maxCount = Math.max(...Object.values(coverageData.coverage_stats).map(data => data.count));
    
    return (
      <div className="coverage-heatmap">
        <h3>Coverage Heatmap ({selectedDays} days)</h3>
        <div className="heatmap-grid">
          {topics.map(topic => {
            const data = coverageData.coverage_stats[topic];
            const intensity = maxCount > 0 ? data.count / maxCount : 0;
            const backgroundColor = `rgba(59, 130, 246, ${intensity})`;
            
            return (
              <div
                key={topic}
                className="heatmap-cell"
                style={{ backgroundColor }}
                title={`${topic}: ${data.count} questions (${data.percentage}%)`}
              >
                <div className="heatmap-topic">{topic}</div>
                <div className="heatmap-count">{data.count}</div>
              </div>
            );
          })}
        </div>
        <div className="heatmap-legend">
          <span>Low</span>
          <div className="legend-gradient"></div>
          <span>High</span>
        </div>
      </div>
    );
  };

  if (!user) {
    return (
      <div className="topic-coverage-page">
        <div className="auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to view your topic coverage statistics.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="topic-coverage-page">
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Loading coverage data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="topic-coverage-page">
        <div className="error">
          <h2>Error Loading Coverage Data</h2>
          <p>{error}</p>
          <button onClick={fetchCoverageData} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="topic-coverage-page">
      <div className="page-header">
        <h1>Topic Coverage Dashboard</h1>
        <p>Track your GCSE Mathematics topic coverage and get personalized suggestions</p>
      </div>

      <div className="controls">
        <div className="time-period-selector">
          <label htmlFor="days-select">Analysis Period:</label>
          <select
            id="days-select"
            value={selectedDays}
            onChange={(e) => setSelectedDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 2 weeks</option>
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 2 months</option>
            <option value={90}>Last 3 months</option>
          </select>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Summary Cards */}
        <div className="summary-cards">
          <div className="summary-card">
            <h3>Total Questions</h3>
            <div className="summary-value">{coverageData?.total_questions || 0}</div>
            <div className="summary-period">in {selectedDays} days</div>
          </div>
          
          <div className="summary-card">
            <h3>Topics Covered</h3>
            <div className="summary-value">
              {coverageData ? Object.keys(coverageData.coverage_stats).length : 0}
            </div>
            <div className="summary-period">different topics</div>
          </div>
          
          <div className="summary-card">
            <h3>Coverage</h3>
            <div className="summary-value">{coverageData?.coverage_percentage || 0}%</div>
            <div className="summary-period">of curriculum</div>
          </div>
        </div>

        {/* Coverage Heatmap */}
        {coverageData && Object.keys(coverageData.coverage_stats).length > 0 && (
          <div className="dashboard-section">
            {generateCoverageHeatmap()}
          </div>
        )}

        {/* Topic Statistics Table */}
        {coverageData && Object.keys(coverageData.coverage_stats).length > 0 && (
          <div className="dashboard-section">
            <h3>Topic Statistics</h3>
            <div className="table-container">
              <table className="coverage-table">
                <thead>
                  <tr>
                    <th 
                      onClick={() => handleSort('topic')}
                      className={sortBy === 'topic' ? `sorted ${sortOrder}` : ''}
                    >
                      Topic {sortBy === 'topic' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      onClick={() => handleSort('count')}
                      className={sortBy === 'count' ? `sorted ${sortOrder}` : ''}
                    >
                      Questions {sortBy === 'count' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      onClick={() => handleSort('percentage')}
                      className={sortBy === 'percentage' ? `sorted ${sortOrder}` : ''}
                    >
                      Percentage {sortBy === 'percentage' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      onClick={() => handleSort('last_generated')}
                      className={sortBy === 'last_generated' ? `sorted ${sortOrder}` : ''}
                    >
                      Last Generated {sortBy === 'last_generated' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th>Subtopics</th>
                  </tr>
                </thead>
                <tbody>
                  {getSortedTopics().map(([topic, data]) => (
                    <tr key={topic}>
                      <td className="topic-name">{topic}</td>
                      <td className="question-count">{data.count}</td>
                      <td className="percentage">{data.percentage}%</td>
                      <td className="last-generated">{formatDate(data.last_generated)}</td>
                      <td className="subtopics">
                        <div className="subtopic-list">
                          {Object.entries(data.subtopics).map(([subtopic, count]) => (
                            <span key={subtopic} className="subtopic-tag">
                              {subtopic} ({count})
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Suggested Topics Widget */}
        {suggestionsData && suggestionsData.suggested_topics.length > 0 && (
          <div className="dashboard-section">
            <h3>Suggested Topics</h3>
            <p className="suggestions-description">
              Based on your recent activity, these topics could use more attention:
            </p>
            <div className="suggestions-grid">
              {suggestionsData.suggested_topics.map((topic, index) => (
                <div key={topic} className="suggestion-card">
                  <div className="suggestion-rank">#{index + 1}</div>
                  <div className="suggestion-topic">{topic}</div>
                  <button 
                    className="generate-button"
                    onClick={() => {
                      // Navigate to question generation with this topic pre-filled
                      window.location.href = `/?topic=${encodeURIComponent(topic)}`;
                    }}
                  >
                    Generate Questions
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {coverageData && Object.keys(coverageData.coverage_stats).length === 0 && (
          <div className="dashboard-section">
            <div className="empty-state">
              <h3>No Coverage Data Yet</h3>
              <p>
                Start generating questions to see your topic coverage statistics here.
                Your progress will be tracked automatically as you use the system.
              </p>
              <button 
                className="generate-button primary"
                onClick={() => window.location.href = '/'}
              >
                Generate Your First Questions
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TopicCoveragePage;