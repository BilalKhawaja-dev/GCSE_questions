import { useState, useCallback } from 'react';
import { QuestionResponse, ApiError } from '../types/api';
import { apiClient } from '../services/apiClient';

interface UseQuestionGenerationState {
  loading: boolean;
  questions: QuestionResponse | null;
  error: ApiError | null;
  progress: number;
  isAsync: boolean;
  generateQuestions: (query: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useQuestionGeneration = (): UseQuestionGenerationState => {
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<QuestionResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [progress, setProgress] = useState(0);
  const [isAsync, setIsAsync] = useState(false);

  const generateQuestions = useCallback(async (query: string) => {
    if (!query.trim()) {
      setError({
        error: {
          type: 'ValidationError',
          message: 'Please enter a query to generate questions.',
          request_id: 'client-validation',
          timestamp: new Date().toISOString(),
          guidance: 'Enter a description of the questions you want, for example: "5 Foundation fractions questions"',
        },
      });
      return;
    }

    if (query.length > 500) {
      setError({
        error: {
          type: 'ValidationError',
          message: 'Query is too long. Please limit your request to 500 characters.',
          request_id: 'client-validation',
          timestamp: new Date().toISOString(),
          guidance: 'Try to be more concise in your request.',
        },
      });
      return;
    }

    setLoading(true);
    setError(null);
    setQuestions(null);
    setProgress(0);
    setIsAsync(false);

    try {
      const result = await apiClient.generateQuestionsFromQuery(query);
      
      // Check if this was an async operation
      if (result.metadata?.async_generation || (result as any).async) {
        setIsAsync(true);
        setProgress(100); // Completed async operation
      } else {
        setProgress(100);
      }
      
      setQuestions(result);
      
      // Handle partial results from timeout
      if (result.metadata?.completion_status === 'partial_timeout') {
        setError({
          error: {
            type: 'TimeoutWarning',
            message: result.metadata.message || 'Request timed out but partial results available',
            request_id: result.request_id || 'timeout-warning',
            timestamp: new Date().toISOString(),
            guidance: 'Consider requesting fewer questions for faster generation',
          },
          suggestions: result.suggestions || [
            'Try requesting fewer questions',
            'Consider breaking large requests into smaller batches'
          ]
        });
      }
      
    } catch (err) {
      const error = err as ApiError;
      
      // Handle timeout errors specifically
      if (error.error?.message?.includes('timeout') || 
          error.error?.message?.includes('504') ||
          error.error?.type === 'TimeoutError') {
        
        // Extract requested count from query for suggestion
        const countMatch = query.match(/(\d+)/);
        const requestedCount = countMatch ? parseInt(countMatch[1]) : 10;
        const suggestedCount = Math.max(1, Math.floor(requestedCount / 2));
        
        setError({
          error: {
            type: 'TimeoutError',
            message: 'Request timed out. Try requesting fewer questions.',
            request_id: error.error?.request_id || 'timeout-error',
            timestamp: new Date().toISOString(),
            guidance: `Large requests can take too long. Try requesting ${suggestedCount} questions instead.`,
          },
          suggestions: [
            `Try requesting ${suggestedCount} questions instead of ${requestedCount}`,
            'Break large requests into smaller batches',
            'Retry the operation - it may complete faster on subsequent attempts'
          ]
        });
      } else {
        setError(error);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const reset = useCallback(() => {
    setLoading(false);
    setQuestions(null);
    setError(null);
    setProgress(0);
    setIsAsync(false);
  }, []);

  return {
    loading,
    questions,
    error,
    progress,
    isAsync,
    generateQuestions,
    clearError,
    reset,
  };
};