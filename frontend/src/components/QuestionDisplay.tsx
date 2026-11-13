import React, { useState } from 'react';
import { QuestionResponse, Question, MarkScheme } from '../types/api';
import FeedbackWidget from './FeedbackWidget';
import { formatMathematicalText } from '../utils/mathFormatting';
import './QuestionDisplay.css';

interface QuestionDisplayProps {
  questionData: QuestionResponse;
  theme?: 'default' | 'pink-floral';
}

const QuestionDisplay: React.FC<QuestionDisplayProps> = ({ questionData, theme = 'default' }) => {
  const [showAllAnswers, setShowAllAnswers] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [showReportIssue, setShowReportIssue] = useState(false);
  const [issueType, setIssueType] = useState('');
  const [issueDescription, setIssueDescription] = useState('');
  const [reportSubmitted, setReportSubmitted] = useState(false);

  const copyAllToClipboard = async (questions: Question[]) => {
    try {
      // Format all questions as plain text
      const text = questions.map((q, index) => {
        const questionNum = index + 1;
        const markScheme = getMarkSchemeForQuestion(q);
        
        return `Question ${questionNum} (${q.marks} marks)
${q.question_text}

Answer:
${markScheme.marking_criteria}

---`;
      }).join('\n\n');
      
      await navigator.clipboard.writeText(text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getMarkSchemeForQuestion = (question: Question) => {
    // First try to find existing mark scheme
    const existingScheme = questionData.mark_scheme?.find(ms => ms.question_id === question.id);
    if (existingScheme) return existingScheme;
    
    // Generate a basic mark scheme if none exists
    const marks = question.marks || 4;
    const methodMarks = Math.ceil(marks * 0.6);
    const accuracyMarks = marks - methodMarks;
    
    return {
      question_id: question.id,
      marking_criteria: `Award ${methodMarks} method mark(s) for correct working shown. Award ${accuracyMarks} accuracy mark(s) for correct final answer.`,
      method_marks: methodMarks,
      accuracy_marks: accuracyMarks
    };
  };

  // Calculate total marks from questions if metadata is not available
  const totalMarks = questionData.metadata?.total_marks ?? 
    (questionData.questions?.reduce((sum, q) => sum + (q.marks || 0), 0) || 0);
  
  // Get generated_at from metadata or root level
  const generatedAt = questionData.metadata?.generated_at || (questionData as any).generated_at;
  
  // Get model version with fallback
  const modelVersion = questionData.metadata?.model_version || 'v2';

  // Get session_id for feedback (use first question's id as fallback)
  const sessionId = (questionData as any).session_id || questionData.questions?.[0]?.id || 'unknown';

  const handleReportIssue = async () => {
    if (!issueType || !issueDescription.trim()) {
      alert('Please select an issue type and provide a description');
      return;
    }

    try {
      // Submit issue report through feedback endpoint
      const response = await fetch(`${process.env.REACT_APP_API_URL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('session_token')}`
        },
        body: JSON.stringify({
          question_id: sessionId,
          helpful: false,
          issue_reported: true,
          issue_type: issueType,
          issue_description: issueDescription
        })
      });

      if (response.ok) {
        setReportSubmitted(true);
        setShowReportIssue(false);
        setTimeout(() => setReportSubmitted(false), 3000);
      } else {
        alert('Failed to submit issue report. Please try again.');
      }
    } catch (error) {
      console.error('Error submitting issue report:', error);
      alert('Failed to submit issue report. Please try again.');
    }
  };

  // Handle async responses that don't have questions yet
  if ((questionData as any).async && !questionData.questions?.length) {
    return (
      <div className="question-display">
        <div className="question-header">
          <h2>Processing Your Request</h2>
          <div className="metadata">
            <span className="status-badge processing">
              {(questionData as any).status || 'Processing'}
            </span>
          </div>
        </div>
        
        <div className="async-status">
          <div className="progress-info">
            <p>{(questionData as any).message || 'Your questions are being generated...'}</p>
            <div className="progress-details">
              <span>Job ID: {(questionData as any).job_id}</span>
              <span>Estimated time: {(questionData as any).estimated_completion_minutes || 2} minutes</span>
            </div>
          </div>
          
          <div className="polling-info">
            <p>The page will automatically update when your questions are ready.</p>
          </div>
        </div>
      </div>
    );
  }

  // Ensure we have questions before rendering
  if (!questionData.questions || questionData.questions.length === 0) {
    return (
      <div className="question-display">
        <div className="question-header">
          <h2>No Questions Available</h2>
        </div>
        <div className="no-questions">
          <p>No questions were generated. Please try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`question-display ${theme === 'pink-floral' ? 'pink-floral' : ''}`}>
      {theme === 'pink-floral' && (
        <>
          <div className="rose-decoration-left">
            <span className="rose-icon">🌹</span>
            <span className="rose-icon">🌹</span>
            <span className="rose-icon">🌹</span>
            <span className="rose-icon">🌹</span>
          </div>
          <div className="rose-decoration-right">
            <span className="rose-icon">🌹</span>
            <span className="rose-icon">🌹</span>
            <span className="rose-icon">🌹</span>
            <span className="rose-icon">🌹</span>
          </div>
        </>
      )}
      
      <div className="question-header">
        <div className="header-left">
          <h2>Generated Questions</h2>
          <div className="metadata">
            <span className="total-marks">Total Marks: {totalMarks}</span>
            <span className="question-count">{questionData.questions.length} Questions</span>
          </div>
        </div>
        <button
          className={`copy-all-button ${copySuccess ? 'success' : ''}`}
          onClick={() => copyAllToClipboard(questionData.questions || [])}
          title="Copy all questions to clipboard"
        >
          {copySuccess ? '✅ Copied!' : '📋 Copy All'}
        </button>
      </div>

      <div className="questions-list">
        {questionData.questions.map((question, index) => {
          const markScheme = getMarkSchemeForQuestion(question);
          
          return (
            <QuestionItem
              key={question.id}
              question={question}
              markScheme={markScheme}
              questionNumber={index + 1}
              showAnswer={showAllAnswers}
            />
          );
        })}
      </div>

      {/* Show Answers Toggle - appears after all questions */}
      <div className="show-answers-section">
        <button
          className={`show-answers-toggle ${showAllAnswers ? 'active' : ''}`}
          onClick={() => setShowAllAnswers(!showAllAnswers)}
          aria-expanded={showAllAnswers}
        >
          <span className="toggle-icon">{showAllAnswers ? '👁️' : '👁️‍🗨️'}</span>
          <span>{showAllAnswers ? 'Hide All Answers' : 'Show All Answers'}</span>
        </button>
      </div>

      {/* Single Feedback Widget at the bottom */}
      <div className="feedback-section">
        <FeedbackWidget 
          questionId={sessionId}
          onFeedbackSubmitted={(feedback) => {
            console.log('Feedback submitted for session', sessionId, feedback);
          }}
        />
        
        {/* Report Issue Button */}
        <div className="report-issue-container">
          {!showReportIssue && !reportSubmitted && (
            <button
              className="report-issue-button"
              onClick={() => setShowReportIssue(true)}
              title="Report an issue with this question"
            >
              🚩 Report Issue
            </button>
          )}
          
          {reportSubmitted && (
            <div className="report-submitted-message">
              ✅ Thank you! Your issue report has been submitted.
            </div>
          )}
          
          {showReportIssue && (
            <div className="report-issue-form">
              <h3>Report an Issue</h3>
              <p>Help us improve by reporting problems with this question.</p>
              
              <div className="form-group">
                <label htmlFor="issue-type">Issue Type:</label>
                <select
                  id="issue-type"
                  value={issueType}
                  onChange={(e) => setIssueType(e.target.value)}
                  className="issue-type-select"
                >
                  <option value="">Select an issue type...</option>
                  <option value="incorrect_answer">Incorrect Answer</option>
                  <option value="ambiguous_wording">Ambiguous Wording</option>
                  <option value="missing_information">Missing Information</option>
                  <option value="wrong_difficulty">Wrong Difficulty Level</option>
                  <option value="formatting_error">Formatting Error</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div className="form-group">
                <label htmlFor="issue-description">Description:</label>
                <textarea
                  id="issue-description"
                  value={issueDescription}
                  onChange={(e) => setIssueDescription(e.target.value)}
                  placeholder="Please describe the issue in detail..."
                  className="issue-description-textarea"
                  rows={4}
                />
              </div>
              
              <div className="form-actions">
                <button
                  className="submit-issue-button"
                  onClick={handleReportIssue}
                >
                  Submit Report
                </button>
                <button
                  className="cancel-issue-button"
                  onClick={() => {
                    setShowReportIssue(false);
                    setIssueType('');
                    setIssueDescription('');
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="generation-info">
        <div className="info-grid">
          {generatedAt && (
            <div className="info-item">
              <span className="info-label">Generated:</span>
              <span className="info-value">{formatDate(generatedAt)}</span>
            </div>
          )}
          <div className="info-item">
            <span className="info-label">Model:</span>
            <span className="info-value">{modelVersion}</span>
          </div>
          {questionData.metadata?.specification_version && (
            <div className="info-item">
              <span className="info-label">Specification:</span>
              <span className="info-value">{questionData.metadata.specification_version}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface QuestionItemProps {
  question: Question;
  markScheme?: MarkScheme;
  questionNumber: number;
  showAnswer: boolean;
}

const QuestionItem: React.FC<QuestionItemProps> = ({ question, markScheme, questionNumber, showAnswer }) => {
  // Handle both question_text and text field names
  const questionText = question.question_text || (question as any).text || 'Question text not available';
  
  // Get answer from question or mark scheme
  const answer = (question as any).answer || (markScheme as any)?.answer || '';

  return (
    <div className="question-item">
      <div className="question-content">
        <div className="question-number-badge">
          Question {questionNumber}
        </div>
        
        <div className="question-details">
          <div className="question-meta">
            <span className={`tier-badge tier-${question.tier.toLowerCase()}`}>{question.tier}</span>
            <span className="topic-badge">{question.topic}</span>
            <span className="marks-badge">{question.marks} mark{question.marks !== 1 ? 's' : ''}</span>
            {question.difficulty_score && (
              <span className="difficulty-badge">Grade: {question.difficulty_score}/9</span>
            )}
          </div>
          
          <div className="question-text">
            <div 
              className="math-content" 
              dangerouslySetInnerHTML={{
                __html: formatMathematicalText(questionText)
              }} 
            />
          </div>
        </div>
      </div>

      {/* Answer & Mark Scheme - controlled by parent's showAnswer state */}
      {showAnswer && (
        <div className="mark-scheme-section visible">
          <div className="mark-scheme-header">
            <span>📝 Answer & Mark Scheme</span>
          </div>
          
          <div className="mark-scheme-content expanded">
            <div className="mark-scheme-details">
              {/* Answer Section */}
              {answer && (
                <div className="answer-section">
                  <h4>✓ Answer:</h4>
                  <div 
                    className="answer-content"
                    dangerouslySetInnerHTML={{
                      __html: formatMathematicalText(answer)
                    }}
                  />
                </div>
              )}
              
              {/* Marking Criteria */}
              {markScheme && (
                <>
                  <div className="marking-criteria">
                    <h4>Marking Guidance:</h4>
                    <div 
                      dangerouslySetInnerHTML={{
                        __html: formatMathematicalText(
                          markScheme.marking_criteria.replace(/^Answer:[\s\S]*?\n\n/, '')
                        )
                      }}
                    />
                  </div>
                  
                  <div className="marks-breakdown">
                    <div className="marks-row">
                      <span className="marks-label">Method marks:</span>
                      <span className="marks-value">{markScheme.method_marks}</span>
                    </div>
                    <div className="marks-row">
                      <span className="marks-label">Accuracy marks:</span>
                      <span className="marks-value">{markScheme.accuracy_marks}</span>
                    </div>
                    <div className="marks-row total">
                      <span className="marks-label">Total:</span>
                      <span className="marks-value">{markScheme.method_marks + markScheme.accuracy_marks}</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionDisplay;