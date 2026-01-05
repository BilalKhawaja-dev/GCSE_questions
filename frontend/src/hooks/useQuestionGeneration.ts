import { useState, useCallback } from 'react';
import { QuestionResponse, ApiError } from '../types/api';
import { apiClient } from '../services/apiClient';

interface UseQuestionGenerationState {
  loading: boolean;
  questions: QuestionResponse | null;
  error: ApiError | null;
  generateQuestions: (query: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useQuestionGeneration = (): UseQuestionGenerationState => {
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<QuestionResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

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

    try {
      const result = await apiClient.generateQuestionsFromQuery(query);
      setQuestions(result);
    } catch (err) {
      setError(err as ApiError);
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
  }, []);

  return {
    loading,
    questions,
    error,
    generateQuestions,
    clearError,
    reset,
  };
};