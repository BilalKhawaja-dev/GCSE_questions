import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../services/apiClient';
import { SessionDetails } from '../types/api';
import QuestionDisplay from '../components/QuestionDisplay';
import './SessionDetailsPage.css';

const SessionDetailsPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { authState } = useAuth();
  const navigate = useNavigate();
  
  const [sessionDetails, setSessionDetails] = useState<SessionDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authState.isAuthenticated) {
      navigate('/');
      return;
    }
    
    if (!sessionId) {
      navigate('/history');
      return;
    }
    
    loadSessionDetails();
  }, [authState.isAuthenticated, sessionId, navigate]);

  const loadSessionDetails = async () => {
    if (!sessionId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const details = await apiClient.getSessionDetails(sessionId);
      setSessionDetails(details);
      
    } catch (err: any) {
      console.error('Failed to load session details:', err);
      setError(err.error?.message || 'Failed to load session details');
    } finally {
      setLoading(false);
    }
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

  const handlePrintQuestions = () => {
    window.print();
  };

  const handleExportQuestions = () => {
    if (!sessionDetails) return;
    
    const content = `GCSE Mathematics Questions - Generated ${formatDate(sessionDetails.timestamp)}

Query: ${sessionDetails.query}
Topic: ${sessionDetails.metadata.topic}
Tier: ${sessionDetails.metadata.tier}
Total Questions: ${sessionDetails.generated_questions.length}
Total Marks: ${sessionDetails.metadata.total_marks}

${sessionDetails.generated_questions.map((question, index) => `
Question ${index + 1} (${question.marks} marks)
${question.question_text}

Topic: ${question.topic}${question.subtopic ? ` - ${question.subtopic}` : ''}
Tier: ${question.tier}
${question.difficulty_score ? `Difficulty: ${question.difficulty_score}/10` : ''}
`).join('\n')}

Generated using GCSE Question Generator v${sessionDetails.metadata.specification_version}
Session ID: ${sessionDetails.session_id}
`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gcse-questions-${sessionId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!authState.isAuthenticated) {
    return null;
  }

  if (loading) {
    return (
      <div className="session-details-page">
        <div className="loading">Loading session details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="session-details-page">
        <div className="error">
          <h2>Error Loading Session</h2>
          <p>{error}</p>
          <div className="error-actions">
            <button onClick={() => loadSessionDetails()}>Try Again</button>
            <button onClick={() => navigate('/history')}>Back to History</button>
          </div>
        </div>
      </div>
    );
  }

  if (!sessionDetails) {
    return (
      <div className="session-details-page">
        <div className="error">
          <h2>Session Not Found</h2>
          <p>The requested session could not be found or you don't have access to it.</p>
          <button onClick={() => navigate('/history')}>Back to History</button>
        </div>
      </div>
    );
  }

  return (
    <div className="session-details-page">
      <div className="session-details-header">
        <div className="header-content">
          <h1>Session Details</h1>
          <div className="header-actions">
            <button 
              className="action-button secondary"
              onClick={() => navigate('/history')}
            >
              ← Back to History
            </button>
            <button 
              className="action-button secondary"
              onClick={handlePrintQuestions}
            >
              🖨️ Print
            </button>
            <button 
              className="action-button primary"
              onClick={handleExportQuestions}
            >
              📄 Export
            </button>
          </div>
        </div>
      </div>

      <div className="session-info-section">
        <div className="session-info-card">
          <h2>Session Information</h2>
          
          <div className="info-grid">
            <div className="info-item">
              <label>Original Query:</label>
              <div className="query-text">{sessionDetails.query}</div>
            </div>
            
            <div className="info-item">
              <label>Generated:</label>
              <div>{formatDate(sessionDetails.timestamp)}</div>
            </div>
            
            <div className="info-item">
              <label>Topic:</label>
              <div className="topic-badge">{sessionDetails.metadata.topic}</div>
            </div>
            
            <div className="info-item">
              <label>Tier:</label>
              <div className={`tier-badge tier-${sessionDetails.metadata.tier.toLowerCase()}`}>
                {sessionDetails.metadata.tier}
              </div>
            </div>
            
            <div className="info-item">
              <label>Questions:</label>
              <div>{sessionDetails.generated_questions.length}</div>
            </div>
            
            <div className="info-item">
              <label>Total Marks:</label>
              <div>{sessionDetails.metadata.total_marks}</div>
            </div>
            
            <div className="info-item">
              <label>Generation Time:</label>
              <div className="generation-time">
                {formatDuration(sessionDetails.metadata.generation_time || 0)}
              </div>
            </div>
            
            <div className="info-item">
              <label>Specification:</label>
              <div className="spec-version">{sessionDetails.metadata.specification_version}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="questions-section">
        <h2>Generated Questions ({sessionDetails.generated_questions.length})</h2>
        
        <div className="questions-container">
          <QuestionDisplay 
            questionData={{
              questions: sessionDetails.generated_questions,
              mark_scheme: [], // Mark schemes are embedded in questions for session details
              metadata: {
                generated_at: new Date(sessionDetails.timestamp * 1000).toISOString(),
                model_version: sessionDetails.metadata.specification_version || 'unknown',
                total_marks: sessionDetails.metadata.total_marks,
                specification_version: sessionDetails.metadata.specification_version
              }
            }}
          />
        </div>
      </div>

      <div className="session-footer">
        <div className="session-id">
          Session ID: {sessionDetails.session_id}
        </div>
        <div className="generation-info">
          Generated using GCSE Question Generator v{sessionDetails.metadata.specification_version}
        </div>
      </div>
    </div>
  );
};

export default SessionDetailsPage;