import axios from 'axios';

// Mock axios before importing apiClient
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock axios.create to return a mock instance
const mockAxiosInstance = {
  post: jest.fn(),
  interceptors: {
    request: {
      use: jest.fn(),
    },
    response: {
      use: jest.fn(),
    },
  },
};

mockedAxios.create.mockReturnValue(mockAxiosInstance as any);

// Now import after mocking
import { apiClient } from './apiClient';
import { InterpretRequest, GenerateRequest } from '../types/api';

describe('ApiClient', () => {
  beforeEach(() => {
    mockAxiosInstance.post.mockClear();
    mockedAxios.create.mockClear();
    // Clear environment variables
    delete process.env.REACT_APP_API_BASE_URL;
    delete process.env.REACT_APP_API_KEY;
  });

  describe('interpretQuery', () => {
    it('makes POST request to /api/interpret endpoint', async () => {
      const mockResponse = {
        data: {
          topic: 'Number',
          tier: 'Foundation' as const,
          count: 5,
          confidence: 0.95,
        },
      };

      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const request: InterpretRequest = { query: 'test query' };
      const result = await apiClient.interpretQuery(request);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/api/interpret', request);
      expect(result).toEqual(mockResponse.data);
    });

    it('throws error when request fails', async () => {
      const mockError = new Error('Network error');
      mockAxiosInstance.post.mockRejectedValue(mockError);

      const request: InterpretRequest = { query: 'test query' };

      await expect(apiClient.interpretQuery(request)).rejects.toThrow('Network error');
    });
  });

  describe('generateQuestions', () => {
    it('makes POST request to /api/generate endpoint', async () => {
      const mockResponse = {
        data: {
          questions: [
            {
              id: 'q1',
              question_text: 'Test question',
              marks: 2,
              tier: 'Foundation' as const,
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
        },
      };

      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const request: GenerateRequest = {
        topic: 'Number',
        tier: 'Foundation',
        count: 5,
      };
      const result = await apiClient.generateQuestions(request);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/api/generate', request);
      expect(result).toEqual(mockResponse.data);
    });

    it('throws error when request fails', async () => {
      const mockError = new Error('Network error');
      mockAxiosInstance.post.mockRejectedValue(mockError);

      const request: GenerateRequest = {
        topic: 'Number',
        tier: 'Foundation',
        count: 5,
      };

      await expect(apiClient.generateQuestions(request)).rejects.toThrow('Network error');
    });
  });

  describe('generateQuestionsFromQuery', () => {
    it('calls interpretQuery then generateQuestions', async () => {
      const mockInterpretResponse = {
        data: {
          topic: 'Number',
          tier: 'Foundation' as const,
          count: 5,
          confidence: 0.95,
        },
      };

      const mockGenerateResponse = {
        data: {
          questions: [
            {
              id: 'q1',
              question_text: 'Test question',
              marks: 2,
              tier: 'Foundation' as const,
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
        },
      };

      mockAxiosInstance.post
        .mockResolvedValueOnce(mockInterpretResponse)
        .mockResolvedValueOnce(mockGenerateResponse);

      const result = await apiClient.generateQuestionsFromQuery('test query');

      expect(mockAxiosInstance.post).toHaveBeenCalledTimes(2);
      expect(mockAxiosInstance.post).toHaveBeenNthCalledWith(1, '/api/interpret', { query: 'test query' });
      expect(mockAxiosInstance.post).toHaveBeenNthCalledWith(2, '/api/generate', {
        topic: 'Number',
        tier: 'Foundation',
        count: 5,
        specification_version: undefined,
      });
      expect(result).toEqual(mockGenerateResponse.data);
    });

    it('passes specification_version when provided in intent', async () => {
      const mockInterpretResponse = {
        data: {
          topic: 'Number',
          tier: 'Foundation' as const,
          count: 5,
          confidence: 0.95,
          specification_version: '2024.1',
        },
      };

      const mockGenerateResponse = {
        data: {
          questions: [],
          mark_scheme: [],
          metadata: {
            generated_at: '2024-12-27T10:30:00Z',
            model_version: 'claude-3-sonnet-20240229',
            total_marks: 0,
          },
        },
      };

      mockAxiosInstance.post
        .mockResolvedValueOnce(mockInterpretResponse)
        .mockResolvedValueOnce(mockGenerateResponse);

      await apiClient.generateQuestionsFromQuery('test query');

      expect(mockAxiosInstance.post).toHaveBeenNthCalledWith(2, '/api/generate', {
        topic: 'Number',
        tier: 'Foundation',
        count: 5,
        specification_version: '2024.1',
      });
    });

    it('throws error when interpretQuery fails', async () => {
      const mockError = new Error('Interpret error');
      mockAxiosInstance.post.mockRejectedValue(mockError);

      await expect(apiClient.generateQuestionsFromQuery('test query')).rejects.toThrow('Interpret error');
    });

    it('throws error when generateQuestions fails', async () => {
      const mockInterpretResponse = {
        data: {
          topic: 'Number',
          tier: 'Foundation' as const,
          count: 5,
          confidence: 0.95,
        },
      };

      const mockError = new Error('Generate error');
      mockAxiosInstance.post
        .mockResolvedValueOnce(mockInterpretResponse)
        .mockRejectedValue(mockError);

      await expect(apiClient.generateQuestionsFromQuery('test query')).rejects.toThrow('Generate error');
    });
  });
});