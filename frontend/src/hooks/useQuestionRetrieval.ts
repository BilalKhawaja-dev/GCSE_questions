/**
 * Custom hook for retrieving verified questions from question bank
 * 
 * Provides fast question retrieval (<100ms) from pre-verified question bank.
 * Falls back to generation if bank is empty.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../services/apiClient';
import { QuestionResponse } from '../types/api';

interface RetrievalOptions {
  topic: string;
  grade: 'foundation' | 'higher';
  paperType: 'P1' | 'P2' | 'P3';
  difficultyMin?: number;
  difficultyMax?: number;
  excludeQuestionIds?: string[];
  count?: number;
}

interface UseQuestionRetrievalReturn {
  retrieveQuestions: (options: RetrievalOptions) => Promise<QuestionResponse>;
  isLoading: boolean;
  error: Error | null;
  response: QuestionResponse | null;
  clearError: () => void;
  usedFallback: boolean;
}

export const useQuestionRetrieval = (): UseQuestionRetrievalReturn => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [response, setResponse] = useState<QuestionResponse | null>(null);
  const [usedFallback, setUsedFallback] = useState(false);

  const retrieveQuestions = useCallback(async (options: RetrievalOptions): Promise<QuestionResponse> => {
    setIsLoading(true);
    setError(null);
    setUsedFallback(false);

    try {
      const result = await apiClient.retrieveQuestions(
        options.topic,
        options.grade,
        options.paperType,
        options.difficultyMin || 1,
        options.difficultyMax || 10,
        options.excludeQuestionIds || [],
        options.count || 5
      );

      // Check if we used fallback to generation
      if ((result.metadata as any)?.source !== 'verified_bank') {
        setUsedFallback(true);
      }

      setResponse(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to retrieve questions');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    retrieveQuestions,
    isLoading,
    error,
    response,
    clearError,
    usedFallback
  };
};

export default useQuestionRetrieval;
