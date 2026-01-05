import React, { useState } from 'react';
import { QuestionResponse } from '../types/api';
import FeedbackWidget from './FeedbackWidget';
import './QuestionDisplay.css';

interface QuestionDisplayProps {
  questionData: QuestionResponse;
}

const QuestionDisplay: React.FC<QuestionDisplayProps> = ({ questionData }) => {
  const [showAllAnswers, setShowAllAnswers] = useState(false);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getMarkSchemeForQuestion = (questionId: string) => {
    return questionData.mark_scheme?.find(ms => ms.question_id === questionId);
  };

  // Calculate total marks from questions if metadata is not available
  const totalMarks = questionData.metadata?.total_marks ?? 
    questionData.questions.reduce((sum, q) => sum + (q.marks || 0), 0);
  
  // Get generated_at from metadata or root level
  const generatedAt = questionData.metadata?.generated_at || (questionData as any).generated_at;
  
  // Get model version with fallback
  const modelVersion = questionData.metadata?.model_version || 'v2';

  // Get session_id for feedback (use first question's id as fallback)
  const sessionId = (questionData as any).session_id || questionData.questions[0]?.id || 'unknown';

  return (
    <div className="question-display">
      <div className="question-header">
        <h2>Generated Questions</h2>
        <div className="metadata">
          <span className="total-marks">Total Marks: {totalMarks}</span>
          <span className="question-count">{questionData.questions.length} Questions</span>
        </div>
      </div>

      <div className="questions-list">
        {questionData.questions.map((question, index) => {
          const markScheme = getMarkSchemeForQuestion(question.id);
          
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
  question: QuestionResponse['questions'][0];
  markScheme?: QuestionResponse['mark_scheme'][0];
  questionNumber: number;
  showAnswer: boolean;
}

const QuestionItem: React.FC<QuestionItemProps> = ({ question, markScheme, questionNumber, showAnswer }) => {
  // Format mathematical text for display
  const formatMathematicalText = (text: string): string => {
    // The text should already be converted from LaTeX to plain text/Unicode by the backend
    // We just need to ensure proper line breaks and spacing for readability
    return text
      .replace(/\n/g, '<br>')
      .replace(/\s+/g, ' ')
      .trim();
  };

  // Handle both question_text and text field names
  const questionText = question.question_text || (question as any).text || 'Question text not available';

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
              <span className="difficulty-badge">Difficulty: {question.difficulty_score}/10</span>
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

      {/* Mark Scheme - controlled by parent's showAnswer state */}
      {markScheme && showAnswer && (
        <div className="mark-scheme-section visible">
          <div className="mark-scheme-header">
            <span>Answer & Mark Scheme</span>
          </div>
          
          <div className="mark-scheme-content expanded">
            <div className="mark-scheme-details">
              <div className="marking-criteria">
                <h4>Marking Criteria:</h4>
                <div 
                  dangerouslySetInnerHTML={{
                    __html: formatMathematicalText(markScheme.marking_criteria)
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
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionDisplay;