import React, { useState } from 'react';
import QueryInput from '../components/QueryInput';
import QuestionDisplay from '../components/QuestionDisplay';
import ErrorDisplay from '../components/ErrorDisplay';
import PresetButtonGrid from '../components/PresetButtonGrid';
import GradeFilter from '../components/GradeFilter';
import { useQuestionGeneration } from '../hooks/useQuestionGeneration';
import { GradeFilterType } from '../data/topicPresets';
import { useTheme } from '../contexts/ThemeContext';
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
  
  const { theme } = useTheme();
  const [query, setQuery] = useState('');
  const [gradeFilter, setGradeFilter] = useState<GradeFilterType>('all');
  const [questionCount, setQuestionCount] = useState<5 | 10 | 15 | 20>(5);
  const [selectedTopics, setSelectedTopics] = useState<Array<{
    name: string;
    count: number;
    tier: string;
  }>>([]);

  const handleQuerySubmit = async (submittedQuery: string) => {
    await generateQuestions(submittedQuery);
  };
  
  const handleGradeFilterChange = (filter: GradeFilterType) => {
    setGradeFilter(filter);
    // Don't rebuild query - let user click topics again with new tier
  };
  
  const handleRetry = () => {
    if (query) {
      generateQuestions(query);
    }
  };
  
  const handleErrorDismiss = () => {
    clearError();
  };
  
  const handlePresetClick = (presetQuery: string) => {
    // Extract ONLY the topic name, no numbers
    // "5 Foundation fractions questions" -> "fractions"
    // "10 Higher quadratics questions" -> "quadratics"
    let topicName = '';
    
    // Try to match with tier
    const withTierMatch = presetQuery.match(/\d+\s+(?:Foundation|Higher)\s+(.+?)\s+questions/i);
    if (withTierMatch) {
      topicName = withTierMatch[1].trim();
    } else {
      // Try without tier
      const withoutTierMatch = presetQuery.match(/\d+\s+(.+?)\s+questions/i);
      if (withoutTierMatch) {
        topicName = withoutTierMatch[1].trim();
      } else {
        // Fallback - just use the query
        topicName = presetQuery;
      }
    }
    
    // Remove any remaining numbers from topic name
    topicName = topicName.replace(/^\d+\s*/, '').trim();
    
    // Get current tier
    const tierText = gradeFilter === 'foundation' ? 'Foundation' : 
                    gradeFilter === 'higher' ? 'Higher' : '';
    
    // Check if topic already exists
    const existingIndex = selectedTopics.findIndex(t => t.name === topicName);
    
    if (existingIndex >= 0) {
      // Remove topic
      const newTopics = selectedTopics.filter((_, i) => i !== existingIndex);
      setSelectedTopics(newTopics);
      
      if (newTopics.length === 0) {
        setQuery('');
      } else {
        // Rebuild query from remaining topics
        const parts = newTopics.map(t => {
          const tier = t.tier ? `${t.tier} ` : '';
          return `${t.count} ${tier}${t.name}`;
        });
        setQuery(parts.join(', '));
      }
    } else {
      // Add new topic with current settings
      const newTopic = {
        name: topicName,
        count: questionCount,
        tier: tierText
      };
      const newTopics = [...selectedTopics, newTopic];
      setSelectedTopics(newTopics);
      
      // Build query: "10 Algebra, 5 Higher Number"
      const parts = newTopics.map(t => {
        const tier = t.tier ? `${t.tier} ` : '';
        return `${t.count} ${tier}${t.name}`;
      });
      setQuery(parts.join(', '));
    }
  };
  
  const handleStartOver = () => {
    reset();
    setSelectedTopics([]);
  };

  return (
    <div className="home-page">
      <div className="home-content">
        {/* Always show the query input and presets */}
        <section className="query-section">
          <div className="controls-row">
            <GradeFilter
              activeFilter={gradeFilter}
              onFilterChange={handleGradeFilterChange}
              theme={theme === 'pink-floral' ? 'pink-floral' : 'default'}
            />
            
            <div className="question-count-toggle">
              <span className="toggle-label">Questions:</span>
              <div className="toggle-buttons">
                <button
                  className={`toggle-btn ${questionCount === 5 ? 'active' : ''}`}
                  onClick={() => setQuestionCount(5)}
                  type="button"
                >
                  5
                </button>
                <button
                  className={`toggle-btn ${questionCount === 10 ? 'active' : ''}`}
                  onClick={() => setQuestionCount(10)}
                  type="button"
                >
                  10
                </button>
                <button
                  className={`toggle-btn ${questionCount === 15 ? 'active' : ''}`}
                  onClick={() => setQuestionCount(15)}
                  type="button"
                >
                  15
                </button>
                <button
                  className={`toggle-btn ${questionCount === 20 ? 'active' : ''}`}
                  onClick={() => setQuestionCount(20)}
                  type="button"
                >
                  20
                </button>
              </div>
            </div>
          </div>
          
          <PresetButtonGrid
            onPresetClick={handlePresetClick}
            loading={loading}
            theme={theme === 'pink-floral' ? 'pink-floral' : 'default'}
            gradeFilter={gradeFilter}
            selectedTopics={selectedTopics.map(t => t.name)}
          />
          
          <QueryInput
            onSubmit={handleQuerySubmit}
            loading={loading}
            disabled={false}
            value={query}
            onChange={setQuery}
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
            <QuestionDisplay questionData={questions} theme={theme} />
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