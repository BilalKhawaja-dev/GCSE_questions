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
            <span className="rose-icon">🌸</span>
            <span className="rose-icon">🌺</span>
            <span className="rose-icon">🌷</span>
          </div>
          <div className="rose-decoration-right">
            <span className="rose-icon">🌹</span>
            <span className="rose-icon">🌸</span>
            <span className="rose-icon">🌺</span>
            <span className="rose-icon">🌷</span>
          </div>
        </>
      )}
      
      <div className="question-header">
        <h2>Generated Questions</h2>
        <div className="metadata">
          <span className="total-marks">Total Marks: {totalMarks}</span>
          <span className="question-count">{questionData.questions.length} Questions</span>
        </div>
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