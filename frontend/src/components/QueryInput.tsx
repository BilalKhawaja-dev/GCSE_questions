import React, { useState, FormEvent } from 'react';
import './QueryInput.css';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  loading: boolean;
  disabled?: boolean;
}

const QueryInput: React.FC<QueryInputProps> = ({ onSubmit, loading, disabled = false }) => {
  const [query, setQuery] = useState('');
  const [charCount, setCharCount] = useState(0);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !loading && !disabled) {
      onSubmit(query.trim());
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= 500) {
      setQuery(value);
      setCharCount(value.length);
    }
  };

  const handleClear = () => {
    setQuery('');
    setCharCount(0);
  };

  const isNearLimit = charCount > 400;
  const isAtLimit = charCount >= 500;

  return (
    <div className="query-input-container">
      <form onSubmit={handleSubmit} className="query-form">
        <div className="input-wrapper">
          <label htmlFor="query-textarea" className="query-label">
            Describe the questions you want to generate
          </label>
          <textarea
            id="query-textarea"
            value={query}
            onChange={handleInputChange}
            placeholder="e.g., 5 Foundation fractions questions, or 3 Higher algebra questions with 4 marks each"
            className={`query-textarea ${isAtLimit ? 'at-limit' : isNearLimit ? 'near-limit' : ''}`}
            rows={4}
            disabled={loading || disabled}
            aria-describedby="char-count query-help"
          />
          <div className="input-footer">
            <div 
              id="char-count" 
              className={`char-count ${isNearLimit ? 'warning' : ''} ${isAtLimit ? 'error' : ''}`}
            >
              {charCount}/500
            </div>
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="clear-button"
                disabled={loading || disabled}
                aria-label="Clear input"
              >
                Clear
              </button>
            )}
          </div>
        </div>
        
        <div className="form-actions">
          <button
            type="submit"
            className="generate-button"
            disabled={!query.trim() || loading || disabled || isAtLimit}
          >
            {loading ? (
              <>
                <span className="loading-spinner" aria-hidden="true"></span>
                Generating Questions...
              </>
            ) : (
              'Generate Questions'
            )}
          </button>
        </div>
        
        <div id="query-help" className="help-text">
          <p>
            <strong>Examples:</strong>
          </p>
          <ul>
            <li>"5 Foundation fractions questions"</li>
            <li>"3 Higher algebra questions with 4 marks each"</li>
            <li>"Foundation geometry questions about angles"</li>
            <li>"Higher statistics questions on data analysis"</li>
          </ul>
        </div>
      </form>
    </div>
  );
};

export default QueryInput;