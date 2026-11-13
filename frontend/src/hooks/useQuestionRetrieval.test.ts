/**
 * Tests for useQuestionRetrieval hook
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useQuestionRetrieval } from './useQuestionRetrieval';
import { apiClient } from '../services/apiClient';

// Mock the API client
jest.mock('../services/apiClient');

describe('useQuestionRetrieval', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with correct default state', () => {
    const { result } = renderHook(() => useQuestionRetrieval());

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.response).toBeNull();
    expect(result.current.usedFallback).toBe(false);
  });

  it('should retrieve questions successfully', async () => {
    const mockResponse = {
      success: true,
      questions: [
        {
          question_id: 'q1',
          stem: 'Solve 2x + 5 = 13',
          options: ['x = 4', 'x = 9', 'x = 3', 'x = 8'],
          correct_answer: 'A',
          rationale: 'Subtract 5 from both sides',
          difficulty: 5,
          verification_confidence: 0.95
        }
      ],
      mark_scheme: [],
      session_id: 'retrieval_123',
      request_id: 'retrieval_123',
      generated_at: '2026-01-13T10:00:00Z',
      metadata: {
        source: 'verified_bank',
        total_available: 50,
        response_time_ms: 45
      }
    };

    (apiClient.retrieveQuestions as jest.Mock).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuestionRetrieval());

    await act(async () => {
      await result.current.retrieveQuestions({
        topic: 'algebra',
        grade: 'foundation',
        paperType: 'P1',
        count: 5
      });
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.response).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
    expect(result.current.usedFallback).toBe(false);
  });

  it('should set loading state during retrieval', async () => {
    const mockResponse = {
      success: true,
      questions: [],
      mark_scheme: [],
      session_id: 'retrieval_123',
      request_id: 'retrieval_123',
      generated_at: '2026-01-13T10:00:00Z',
      metadata: {
        source: 'verified_bank'
      }
    };

    (apiClient.retrieveQuestions as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockResponse), 100))
    );

    const { result } = renderHook(() => useQuestionRetrieval());

    act(() => {
      result.current.retrieveQuestions({
        topic: 'algebra',
        grade: 'foundation',
        paperType: 'P1'
      });
    });

    // Should be loading immediately
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should handle errors correctly', async () => {
    const mockError = new Error('Failed to retrieve questions');
    (apiClient.retrieveQuestions as jest.Mock).mockRejectedValue(mockError);

    const { result } = renderHook(() => useQuestionRetrieval());

    await act(async () => {
      try {
        await result.current.retrieveQuestions({
          topic: 'algebra',
          grade: 'foundation',
          paperType: 'P1'
        });
      } catch (error) {
        // Expected to throw
      }
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toEqual(mockError);
    expect(result.current.response).toBeNull();
  });

  it('should detect fallback to generation', async () => {
    const mockResponse = {
      success: true,
      questions: [
        {
          question_id: 'q1',
          stem: 'Generated question',
          options: ['A', 'B', 'C', 'D'],
          correct_answer: 'A',
          rationale: 'Explanation',
          difficulty: 5
        }
      ],
      mark_scheme: [],
      session_id: 'gen_123',
      request_id: 'gen_123',
      generated_at: '2026-01-13T10:00:00Z',
      metadata: {
        source: 'generation',  // Not from verified bank
        model_version: 'claude-3-haiku'
      }
    };

    (apiClient.retrieveQuestions as jest.Mock).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuestionRetrieval());

    await act(async () => {
      await result.current.retrieveQuestions({
        topic: 'algebra',
        grade: 'foundation',
        paperType: 'P1'
      });
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.usedFallback).toBe(true);
  });

  it('should clear error when clearError is called', async () => {
    const mockError = new Error('Test error');
    (apiClient.retrieveQuestions as jest.Mock).mockRejectedValue(mockError);

    const { result } = renderHook(() => useQuestionRetrieval());

    await act(async () => {
      try {
        await result.current.retrieveQuestions({
          topic: 'algebra',
          grade: 'foundation',
          paperType: 'P1'
        });
      } catch (error) {
        // Expected
      }
    });

    await waitFor(() => {
      expect(result.current.error).toEqual(mockError);
    });

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });

  it('should pass all options to API client', async () => {
    const mockResponse = {
      success: true,
      questions: [],
      mark_scheme: [],
      session_id: 'retrieval_123',
      request_id: 'retrieval_123',
      generated_at: '2026-01-13T10:00:00Z',
      metadata: {
        source: 'verified_bank'
      }
    };

    (apiClient.retrieveQuestions as jest.Mock).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuestionRetrieval());

    const options = {
      topic: 'algebra',
      grade: 'foundation' as const,
      paperType: 'P1' as const,
      difficultyMin: 3,
      difficultyMax: 7,
      excludeQuestionIds: ['q1', 'q2'],
      count: 10
    };

    await act(async () => {
      await result.current.retrieveQuestions(options);
    });

    expect(apiClient.retrieveQuestions).toHaveBeenCalledWith(
      'algebra',
      'foundation',
      'P1',
      3,
      7,
      ['q1', 'q2'],
      10
    );
  });

  it('should use default values for optional parameters', async () => {
    const mockResponse = {
      success: true,
      questions: [],
      mark_scheme: [],
      session_id: 'retrieval_123',
      request_id: 'retrieval_123',
      generated_at: '2026-01-13T10:00:00Z',
      metadata: {
        source: 'verified_bank'
      }
    };

    (apiClient.retrieveQuestions as jest.Mock).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuestionRetrieval());

    await act(async () => {
      await result.current.retrieveQuestions({
        topic: 'algebra',
        grade: 'foundation',
        paperType: 'P1'
      });
    });

    expect(apiClient.retrieveQuestions).toHaveBeenCalledWith(
      'algebra',
      'foundation',
      'P1',
      1,    // default difficultyMin
      10,   // default difficultyMax
      [],   // default excludeQuestionIds
      5     // default count
    );
  });

  it('should handle multiple sequential retrievals', async () => {
    const mockResponse1 = {
      success: true,
      questions: [{ question_id: 'q1' }],
      mark_scheme: [],
      session_id: 'retrieval_1',
      request_id: 'retrieval_1',
      generated_at: '2026-01-13T10:00:00Z',
      metadata: { source: 'verified_bank' }
    };

    const mockResponse2 = {
      success: true,
      questions: [{ question_id: 'q2' }],
      mark_scheme: [],
      session_id: 'retrieval_2',
      request_id: 'retrieval_2',
      generated_at: '2026-01-13T10:00:00Z',
      metadata: { source: 'verified_bank' }
    };

    (apiClient.retrieveQuestions as jest.Mock)
      .mockResolvedValueOnce(mockResponse1)
      .mockResolvedValueOnce(mockResponse2);

    const { result } = renderHook(() => useQuestionRetrieval());

    // First retrieval
    await act(async () => {
      await result.current.retrieveQuestions({
        topic: 'algebra',
        grade: 'foundation',
        paperType: 'P1'
      });
    });

    await waitFor(() => {
      expect(result.current.response).toEqual(mockResponse1);
    });

    // Second retrieval
    await act(async () => {
      await result.current.retrieveQuestions({
        topic: 'geometry',
        grade: 'higher',
        paperType: 'P2'
      });
    });

    await waitFor(() => {
      expect(result.current.response).toEqual(mockResponse2);
    });

    expect(apiClient.retrieveQuestions).toHaveBeenCalledTimes(2);
  });
});
