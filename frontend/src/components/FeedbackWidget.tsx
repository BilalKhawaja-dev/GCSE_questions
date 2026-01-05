import React, { useState } from 'react';
import { apiClient } from '../services/apiClient';
import './FeedbackWidget.css';

interface FeedbackWidgetProps {
  questionId: string;
  onFeedbackSubmitted?: (feedback: { helpful: boolean; difficultyRating: number; comments?: string }) => void;
}

const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({ questionId, onFeedbackSubmitted }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [helpful, setHelpful] = useState<boolean | null>(null);
  const [difficultyRating, setDifficultyRating] = useState<number>(5);
  const [comments, setComments] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleHelpfulClick = (isHelpful: boolean) => {
    setHelpful(isHelpful);
    setError(null);
  };

  const handleDifficultyChange = (rating: number) => {
    setDifficultyRating(rating);
  };

  const handleSubmit = async () => {
    if (helpful === null) {
      setError('Please indicate if this question was helpful');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.submitFeedback(questionId, helpful, difficultyRating, comments);
      setIsSubmitted(true);
      
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted({ helpful, difficultyRating, comments });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setIsSubmitted(false);
    setHelpful(null);
    setDifficultyRating(5);
    setComments('');
    setError(null);
    setIsExpanded(false);
  };

  if (isSubmitted) {
    return (
      <div className="feedback-widget submitted">
        <div className="feedback-success">
          <span className="success-icon">✓</span>
          <span className="success-message">Thank you for your feedback!</span>
          <button 
            className="feedback-reset-btn"
            onClick={handleReset}
            aria-label="Provide more feedback"
          >
            Edit
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="feedback-widget">
      <div className="feedback-header">
        <span className="feedback-label">Was this question helpful?</span>
        <div className="helpful-buttons">
          <button
            className={`helpful-btn ${helpful === true ? 'selected' : ''}`}
            onClick={() => handleHelpfulClick(true)}
            aria-label="Mark as helpful"
            disabled={isSubmitting}
          >
            👍 Yes
          </button>
          <button
            className={`helpful-btn ${helpful === false ? 'selected' : ''}`}
            onClick={() => handleHelpfulClick(false)}
            aria-label="Mark as not helpful"
            disabled={isSubmitting}
          >
            👎 No
          </button>
        </div>
        
        <button
          className={`expand-btn ${isExpanded ? 'expanded' : ''}`}
          onClick={() => setIsExpanded(!isExpanded)}
          aria-label={isExpanded ? 'Hide additional feedback options' : 'Show additional feedback options'}
          disabled={isSubmitting}
        >
          {isExpanded ? 'Less' : 'More'}
        </button>
      </div>

      {isExpanded && (
        <div className="feedback-details">
          <div className="difficulty-rating">
            <label className="rating-label">
              How difficult was this question? (1 = Very Easy, 10 = Very Hard)
            </label>
            <div className="rating-slider-container">
              <input
                type="range"
                min="1"
                max="10"
                value={difficultyRating}
                onChange={(e) => handleDifficultyChange(parseInt(e.target.value))}
                className="rating-slider"
                disabled={isSubmitting}
                aria-label={`Difficulty rating: ${difficultyRating} out of 10`}
              />
              <div className="rating-display">
                <span className="rating-value">{difficultyRating}</span>
                <span className="rating-scale">/10</span>
              </div>
            </div>
            <div className="rating-labels">
              <span className="rating-label-start">Very Easy</span>
              <span className="rating-label-end">Very Hard</span>
            </div>
          </div>

          <div className="comments-section">
            <label htmlFor={`comments-${questionId}`} className="comments-label">
              Additional comments (optional):
            </label>
            <textarea
              id={`comments-${questionId}`}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Any specific feedback about this question..."
              className="comments-textarea"
              maxLength={500}
              disabled={isSubmitting}
              rows={3}
            />
            <div className="character-count">
              {comments.length}/500
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="feedback-error" role="alert">
          {error}
        </div>
      )}

      <div className="feedback-actions">
        <button
          className="submit-feedback-btn"
          onClick={handleSubmit}
          disabled={isSubmitting || helpful === null}
          aria-label="Submit feedback"
        >
          {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
        </button>
      </div>
    </div>
  );
};

export default FeedbackWidget;