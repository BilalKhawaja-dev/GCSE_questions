import React from 'react';
import QueryInput from '../components/QueryInput';
import QuestionDisplay from '../components/QuestionDisplay';
import ErrorDisplay from '../components/ErrorDisplay';
import { useQuestionGeneration } from '../hooks/useQuestionGeneration';
import './HomePage.css';

const HomePage: React.FC = () => {
  const {
    loading,
    questions,
    error,
    generateQuestions,
    clearError,
    reset,
  } = useQuestionGeneration();

  const handleQuerySubmit = async (query: string) => {
    await generateQuestions(query);
  };

  const handleRetry = () => {
    clearError();
    // The user will need to submit the query again
  };

  const handleErrorDismiss = () => {
    clearError();
  };

  const handleStartOver = () => {
    reset();
  };

  return (
    <div className="home-page">
      <div className="home-content">
        {/* Always show the query input */}
        <section className="query-section">
          <QueryInput
            onSubmit={handleQuerySubmit}
            loading={loading}
            disabled={false}
          />
        </section>

        {/* Show loading state */}
        {loading && (
          <section className="loading-section">
            <div className="loading-container">
              <div className="loading-spinner-large" aria-hidden="true"></div>
              <h3>Generating your questions...</h3>
              <p>This may take up to 60 seconds. Please wait.</p>
            </div>
          </section>
        )}

        {/* Show error if there is one */}
        {error && !loading && (
          <section className="error-section">
            <ErrorDisplay
              error={error}
              onRetry={handleRetry}
              onDismiss={handleErrorDismiss}
            />
          </section>
        )}

        {/* Show questions if available */}
        {questions && !loading && !error && (
          <section className="results-section">
            <div className="results-header">
              <button
                className="start-over-button"
                onClick={handleStartOver}
                type="button"
              >
                Generate New Questions
              </button>
            </div>
            <QuestionDisplay questionData={questions} />
          </section>
        )}

        {/* Show welcome message when no questions and no loading */}
        {!questions && !loading && !error && (
          <section className="welcome-section">
            <div className="welcome-content">
              <h2>Welcome to the GCSE Question Generator</h2>
              <p>
                Generate high-quality GCSE exam questions tailored to your needs. 
                Simply describe what you're looking for in the box above.
              </p>
              
              <div className="quick-actions">
                <a href="/history" className="quick-action-link">
                  📚 View Your Session History
                </a>
              </div>
              
              <div className="features-grid">
                <div className="feature-card">
                  <div className="feature-icon">📝</div>
                  <h3>Natural Language</h3>
                  <p>Describe questions in plain English - no complex syntax required</p>
                </div>
                
                <div className="feature-card">
                  <div className="feature-icon">🎯</div>
                  <h3>Curriculum Aligned</h3>
                  <p>Questions based on official Edexcel GCSE specifications</p>
                </div>
                
                <div className="feature-card">
                  <div className="feature-icon">📊</div>
                  <h3>Complete Mark Schemes</h3>
                  <p>Every question comes with detailed marking criteria</p>
                </div>
                
                <div className="feature-card">
                  <div className="feature-icon">🧮</div>
                  <h3>Math Notation</h3>
                  <p>Proper mathematical formatting with LaTeX rendering</p>
                </div>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
};

export default HomePage;