import { renderHook, act } from '@testing-library/react';
import { useQuestionGeneration } from './useQuestionGeneration';
import { apiClient } from '../services/apiClient';
import { QuestionResponse } from '../types/api';

// Mock the API client
jest.mock('../services/apiClient', () => ({
  apiClient: {
    generateQuestionsFromQuery: jest.fn(),
  },
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

const mockQuestionResponse: QuestionResponse = {
  questions: [
    {
      id: 'q1',
      question_text: 'Test question',
      marks: 2,
      tier: 'Foundation',
      topic: 'Number',
    },
  ],
  mark_scheme: [
    {
      question_id: 'q1',
      marking_criteria: 'Test criteria',
      method_marks: 1,
      accuracy_marks: 1,
    },
  ],
  metadata: {
    generated_at: '2024-12-27T10:30:00Z',
    model_version: 'claude-3-sonnet-20240229',
    total_marks: 2,
  },
};

describe('useQuestionGeneration', () => {
  beforeEach(() => {
    mockApiClient.generateQuestionsFromQuery.mockClear();
  });

  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useQuestionGeneration());

    expect(result.current.loading).toBe(false);
    expect(result.current.questions).toBe(null);
    expect(result.current.error).toBe(null);
  });

  it('sets loading state when generating questions', async () => {
    mockApiClient.generateQuestionsFromQuery.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockQuestionResponse), 100))
    );

    const { result } = renderHook(() => useQuestionGeneration());

    act(() => {
      result.current.generateQuestions('test query');
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBe(null);
    expect(result.current.questions).toBe(null);
  });

  it('sets questions and clears loading on successful generation', async () => {
    mockApiClient.generateQuestionsFromQuery.mockResolvedValue(mockQuestionResponse);

    const { result } = renderHook(() => useQuestionGeneration());

    await act(async () => {
      await result.current.generateQuestions('test query');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.questions).toEqual(mockQuestionResponse);
    expect(result.current.error).toBe(null);
  });

  it('sets error and clears loading on failed generation', async () => {
    const mockError = {
      error: {
        type: 'ServiceUnavailable' as const,
        message: 'Service is down',
        request_id: 'req-123',
        timestamp: '2024-12-27T10:30:00Z',
      },
    };

    mockApiClient.generateQuestionsFromQuery.mockRejectedValue(mockError);

    const { result } = renderHook(() => useQuestionGeneration());

    await act(async () => {
      await result.current.generateQuestions('test query');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.questions).toBe(null);
    expect(result.current.error).toEqual(mockError);
  });

  it('validates empty query', async () => {
    const { result } = renderHook(() => useQuestionGeneration());

    await act(async () => {
      await result.current.generateQuestions('');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.questions).toBe(null);
    expect(result.current.error).toEqual({
      error: {
        type: 'ValidationError',
        message: 'Please enter a query to generate questions.',
        request_id: 'client-validation',
        timestamp: expect.any(String),
        guidance: 'Enter a description of the questions you want, for example: "5 Foundation fractions questions"',
      },
    });

    expect(mockApiClient.generateQuestionsFromQuery).not.toHaveBeenCalled();
  });

  it('validates query with only whitespace', async () => {
    const { result } = renderHook(() => useQuestionGeneration());

    await act(async () => {
      await result.current.generateQuestions('   ');
    });

    expect(result.current.error?.error.type).toBe('ValidationError');
    expect(mockApiClient.generateQuestionsFromQuery).not.toHaveBeenCalled();
  });

  it('validates query length over 500 characters', async () => {
    const { result } = renderHook(() => useQuestionGeneration());
    const longQuery = 'a'.repeat(501);

    await act(async () => {
      await result.current.generateQuestions(longQuery);
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.questions).toBe(null);
    expect(result.current.error).toEqual({
      error: {
        type: 'ValidationError',
        message: 'Query is too long. Please limit your request to 500 characters.',
        request_id: 'client-validation',
        timestamp: expect.any(String),
        guidance: 'Try to be more concise in your request.',
      },
    });

    expect(mockApiClient.generateQuestionsFromQuery).not.toHaveBeenCalled();
  });

  it('allows query with exactly 500 characters', async () => {
    mockApiClient.generateQuestionsFromQuery.mockResolvedValue(mockQuestionResponse);

    const { result } = renderHook(() => useQuestionGeneration());
    const maxLengthQuery = 'a'.repeat(500);

    await act(async () => {
      await result.current.generateQuestions(maxLengthQuery);
    });

    expect(result.current.error).toBe(null);
    expect(mockApiClient.generateQuestionsFromQuery).toHaveBeenCalledWith(maxLengthQuery);
  });

  it('clears error when clearError is called', async () => {
    const mockError = {
      error: {
        type: 'ServiceUnavailable' as const,
        message: 'Service is down',
        request_id: 'req-123',
        timestamp: '2024-12-27T10:30:00Z',
      },
    };

    mockApiClient.generateQuestionsFromQuery.mockRejectedValue(mockError);

    const { result } = renderHook(() => useQuestionGeneration());

    await act(async () => {
      await result.current.generateQuestions('test query');
    });

    expect(result.current.error).toEqual(mockError);

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBe(null);
  });

  it('resets all state when reset is called', async () => {
    mockApiClient.generateQuestionsFromQuery.mockResolvedValue(mockQuestionResponse);

    const { result } = renderHook(() => useQuestionGeneration());

    await act(async () => {
      await result.current.generateQuestions('test query');
    });

    expect(result.current.questions).toEqual(mockQuestionResponse);

    act(() => {
      result.current.reset();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.questions).toBe(null);
    expect(result.current.error).toBe(null);
  });

  it('calls API with trimmed query', async () => {
    mockApiClient.generateQuestionsFromQuery.mockResolvedValue(mockQuestionResponse);

    const { result } = renderHook(() => useQuestionGeneration());

    await act(async () => {
      await result.current.generateQuestions('  test query  ');
    });

    expect(mockApiClient.generateQuestionsFromQuery).toHaveBeenCalledWith('  test query  ');
  });
});