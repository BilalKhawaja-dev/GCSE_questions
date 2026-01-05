import React, { useState } from 'react';
import { SessionDetails as SessionDetailsType } from '../types/api';
import QuestionDisplay from './QuestionDisplay';
import apiClient from '../services/apiClient';
import './SessionDetails.css';

interface SessionDetailsProps {
  sessionDetails: SessionDetailsType;
  onClose: () => void;
}

const SessionDetails: React.FC<SessionDetailsProps> = ({ sessionDetails, onClose }) => {
  const [isExporting, setIsExporting] = useState(false);

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleExportToPDF = async () => {
    try {
      setIsExporting(true);
      
      const { filename, pdfData } = await apiClient.exportSessionToPDF(sessionDetails.session_id);
      
      // Convert base64 to blob and trigger download
      const byteCharacters = atob(pdfData);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'application/pdf' });
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
    } catch (error: any) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error.message || 'Unknown error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="session-details-overlay">
      <div className="session-details-modal">
        <div className="session-details-header">
          <div className="session-info">
            <h2>Session Details</h2>
            <div className="session-metadata">
              <div className="metadata-item">
                <span className="label">Query:</span>
                <span className="value">{sessionDetails.query}</span>
              </div>
              <div className="metadata-item">
                <span className="label">Generated:</span>
                <span className="value">{formatDate(sessionDetails.timestamp)}</span>
              </div>
              <div className="metadata-item">
                <span className="label">Topic:</span>
                <span className="value topic-badge">{sessionDetails.metadata.topic}</span>
              </div>
              <div className="metadata-item">
                <span className="label">Tier:</span>
                <span className={`value tier-badge tier-${sessionDetails.metadata.tier.toLowerCase()}`}>
                  {sessionDetails.metadata.tier}
                </span>
              </div>
              <div className="metadata-item">
                <span className="label">Questions:</span>
                <span className="value">{sessionDetails.metadata.question_count}</span>
              </div>
              <div className="metadata-item">
                <span className="label">Total Marks:</span>
                <span className="value">{sessionDetails.metadata.total_marks}</span>
              </div>
              {sessionDetails.metadata.generation_time && (
                <div className="metadata-item">
                  <span className="label">Generation Time:</span>
                  <span className="value">{sessionDetails.metadata.generation_time.toFixed(1)}s</span>
                </div>
              )}
              {sessionDetails.metadata.specification_version && (
                <div className="metadata-item">
                  <span className="label">Specification:</span>
                  <span className="value">{sessionDetails.metadata.specification_version}</span>
                </div>
              )}
            </div>
          </div>
          
          <button onClick={onClose} className="close-button" aria-label="Close">
            ×
          </button>
        </div>

        <div className="session-content">
          <div className="questions-section">
            <h3>Generated Questions</h3>
            <div className="questions-list">
              {sessionDetails.generated_questions.map((question, index) => (
                <div key={question.id} className="question-container">
                  <div className="question-number">Question {index + 1}</div>
                  <QuestionDisplay 
                    questionData={{
                      questions: [question],
                      mark_scheme: [], // Mark schemes are embedded in the question text for this display
                      metadata: {
                        generated_at: new Date(sessionDetails.timestamp * 1000).toISOString(),
                        model_version: sessionDetails.metadata.specification_version || 'unknown',
                        total_marks: question.marks,
                        specification_version: sessionDetails.metadata.specification_version
                      }
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="session-actions">
          <button 
            onClick={() => {
              // Copy session content to clipboard
              const content = `Session: ${sessionDetails.query}\n\n` +
                sessionDetails.generated_questions.map((q, i) => 
                  `Question ${i + 1}:\n${q.question_text}\n\nMarks: ${q.marks}\n\n`
                ).join('');
              
              navigator.clipboard.writeText(content).then(() => {
                alert('Session content copied to clipboard!');
              }).catch(() => {
                alert('Failed to copy content to clipboard');
              });
            }}
            className="copy-button"
          >
            Copy to Clipboard
          </button>
          
          <button 
            onClick={handleExportToPDF}
            disabled={isExporting}
            className="export-button"
          >
            {isExporting ? 'Exporting...' : 'Export to PDF'}
          </button>
          
          <button 
            onClick={() => {
              // Generate new questions with the same query
              // This would trigger the parent component to navigate to question generation
              // For now, we'll just close the modal
              onClose();
            }}
            className="regenerate-button"
          >
            Generate Similar Questions
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionDetails;