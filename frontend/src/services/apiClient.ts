import axios, { AxiosInstance, AxiosError } from 'axios';
import { 
  InterpretRequest, 
  GenerateRequest, 
  QueryIntent, 
  QuestionResponse, 
  ApiError,
  AuthRequest,
  AuthResponse,
  AuthState,
  SessionHistoryResponse,
  SessionDetails,
  SessionStatistics
} from '../types/api';

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;
  private apiKey: string;
  private authState: AuthState;

  constructor() {
    // Get API configuration from environment variables
    this.baseURL = process.env.REACT_APP_API_BASE_URL || 'https://api.gcse-questions.example.com';
    this.apiKey = process.env.REACT_APP_API_KEY || '';

    // Initialize auth state from localStorage
    this.authState = this.loadAuthState();

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 120000, // 2 minutes timeout
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
      },
    });

    // Add request interceptor for logging and authentication
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        
        // Add Authorization header if authenticated
        if (this.authState.isAuthenticated && this.authState.sessionToken) {
          config.headers.Authorization = `Bearer ${this.authState.sessionToken}`;
        }
        
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error: AxiosError) => {
        console.error('API Response Error:', error);
        
        // Handle authentication errors
        if (error.response?.status === 401 || error.response?.status === 403) {
          this.clearAuthState();
        }
        
        return Promise.reject(this.handleApiError(error));
      }
    );
  }

  private loadAuthState(): AuthState {
    try {
      const stored = localStorage.getItem('authState');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Check if session is expired
        if (parsed.expiresAt && new Date(parsed.expiresAt) > new Date()) {
          return {
            ...parsed,
            expiresAt: new Date(parsed.expiresAt)
          };
        }
      }
    } catch (error) {
      console.error('Error loading auth state:', error);
    }
    
    return {
      isAuthenticated: false,
      user: null,
      sessionToken: null,
      expiresAt: null
    };
  }

  private saveAuthState(): void {
    try {
      localStorage.setItem('authState', JSON.stringify(this.authState));
    } catch (error) {
      console.error('Error saving auth state:', error);
    }
  }

  private clearAuthState(): void {
    this.authState = {
      isAuthenticated: false,
      user: null,
      sessionToken: null,
      expiresAt: null
    };
    localStorage.removeItem('authState');
  }

  private handleApiError(error: AxiosError): ApiError {
    if (error.response?.data) {
      // Server returned an error response
      return error.response.data as ApiError;
    } else if (error.request) {
      // Network error or timeout
      return {
        error: {
          type: 'ServiceUnavailable',
          message: 'Unable to connect to the service. Please check your internet connection and try again.',
          request_id: 'client-error',
          timestamp: new Date().toISOString(),
          guidance: 'Please try again in a few moments. If the problem persists, contact support.',
        },
      };
    } else {
      // Other error
      return {
        error: {
          type: 'InternalError',
          message: 'An unexpected error occurred.',
          request_id: 'client-error',
          timestamp: new Date().toISOString(),
          guidance: 'Please try again. If the problem persists, contact support.',
        },
      };
    }
  }

  // Authentication methods
  async register(username: string, password: string, email: string, school?: string, subjectSpecialization?: string): Promise<AuthResponse> {
    try {
      const request: AuthRequest = {
        action: 'register',
        username,
        password,
        email,
        school,
        subject_specialization: subjectSpecialization
      };
      
      const response = await this.client.post<AuthResponse>('/auth', request);
      
      if (response.data.success && response.data.session_token && response.data.user_id) {
        this.authState = {
          isAuthenticated: true,
          user: {
            username: response.data.user_id,
            email,
            school,
            subject_specialization: subjectSpecialization
          },
          sessionToken: response.data.session_token,
          expiresAt: response.data.expires_at ? new Date(response.data.expires_at) : null
        };
        this.saveAuthState();
      }
      
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async login(username: string, password: string): Promise<AuthResponse> {
    try {
      const request: AuthRequest = {
        action: 'login',
        username,
        password
      };
      
      const response = await this.client.post<AuthResponse>('/auth', request);
      
      if (response.data.success && response.data.session_token && response.data.user_id) {
        this.authState = {
          isAuthenticated: true,
          user: {
            username: response.data.user_id,
            email: '', // Will be populated from user profile if needed
          },
          sessionToken: response.data.session_token,
          expiresAt: response.data.expires_at ? new Date(response.data.expires_at) : null
        };
        this.saveAuthState();
      }
      
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async logout(): Promise<void> {
    this.clearAuthState();
  }

  async validateSession(): Promise<boolean> {
    if (!this.authState.sessionToken) {
      return false;
    }
    
    try {
      const request: AuthRequest = {
        action: 'validate',
        session_token: this.authState.sessionToken
      };
      
      const response = await this.client.post<AuthResponse>('/auth', request);
      
      if (!response.data.success) {
        this.clearAuthState();
        return false;
      }
      
      return true;
    } catch (error) {
      this.clearAuthState();
      return false;
    }
  }

  getAuthState(): AuthState {
    return { ...this.authState };
  }

  isAuthenticated(): boolean {
    return this.authState.isAuthenticated && 
           this.authState.sessionToken !== null &&
           (this.authState.expiresAt === null || this.authState.expiresAt > new Date());
  }

  async interpretQuery(request: InterpretRequest): Promise<{ intent: QueryIntent; enriched_prompt?: string }> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      // Add authentication info to request
      const authenticatedRequest = {
        ...request,
        user_id: this.authState.user?.username,
        session_token: this.authState.sessionToken
      };
      
      const response = await this.client.post<{ intent: QueryIntent; enriched_prompt?: string }>('/interpret', authenticatedRequest);
      // Return both intent and enriched_prompt
      return {
        intent: response.data.intent,
        enriched_prompt: response.data.enriched_prompt
      };
    } catch (error) {
      throw error;
    }
  }

  async generateQuestions(request: GenerateRequest & { enriched_prompt?: string }): Promise<QuestionResponse> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      // Add authentication info to request
      const authenticatedRequest = {
        ...request,
        user_id: this.authState.user?.username,
        session_token: this.authState.sessionToken
      };
      
      // Use regular API Gateway endpoint (Function URL has CORS issues)
      const response = await this.client.post<QuestionResponse>('/generate', authenticatedRequest);
      
      // Check if this is an async response
      if (response.data.async) {
        // For async responses, poll for completion
        return this.pollAsyncGeneration(response.data);
      }
      
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  private async pollAsyncGeneration(asyncResponse: any): Promise<QuestionResponse> {
    const { job_id, session_id, polling_info } = asyncResponse;
    const maxWaitTime = (polling_info?.max_wait_time_minutes || 5) * 60 * 1000; // Convert to ms
    const pollInterval = (polling_info?.recommended_poll_interval_seconds || 5) * 1000; // Convert to ms
    const startTime = Date.now();
    
    console.log(`Polling for async generation completion. Job ID: ${job_id}, Session ID: ${session_id}`);
    
    while (Date.now() - startTime < maxWaitTime) {
      try {
        // Check session status
        const sessionDetails = await this.getSessionDetails(session_id);
        
        const status = sessionDetails.metadata?.status;
        const progress = sessionDetails.metadata?.progress || 0;
        
        console.log(`Job ${job_id} status: ${status} (${progress}%)`);
        
        if (status === 'completed') {
          // Convert session details to QuestionResponse format
          return {
            success: true,
            questions: sessionDetails.generated_questions || [],
            mark_scheme: [], // Will be generated from questions
            session_id: session_id,
            request_id: sessionDetails.metadata?.request_id || job_id,
            generated_at: sessionDetails.metadata?.completed_at || new Date().toISOString(),
            metadata: {
              total_marks: sessionDetails.metadata?.total_marks || 0,
              model_version: 'claude-3-sonnet',
              generated_at: sessionDetails.metadata?.completed_at || new Date().toISOString(),
              async_generation: true,
              job_id: job_id,
              generation_time: sessionDetails.metadata?.generation_time
            }
          };
        } else if (status === 'failed') {
          throw new Error(`Async generation failed: ${sessionDetails.metadata?.error || 'Unknown error'}`);
        }
        
        // Still processing, wait and try again
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        
      } catch (error) {
        console.error('Error polling async generation:', error);
        // Continue polling unless it's a critical error
        if (error instanceof Error && error.message?.includes('Authentication required')) {
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    // Timeout reached
    throw new Error(`Async generation timed out after ${maxWaitTime / 1000} seconds. Job ID: ${job_id}. Check session ${session_id} for status.`);
  }

  // Combined method for the full workflow - SIMPLIFIED: Skip InterpretLambda
  async generateQuestionsFromQuery(query: string): Promise<QuestionResponse> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      // Parse the query on the client side to extract count
      const countMatch = query.match(/(\d+)/);
      const count = countMatch ? parseInt(countMatch[1]) : 5;
      
      // Determine tier from query
      let tier: 'Foundation' | 'Higher' = 'Foundation';
      if (query.toLowerCase().includes('higher')) {
        tier = 'Higher';
      }
      
      // Extract topic - use first recognizable topic or default to the query
      const topics = ['algebra', 'number', 'geometry', 'statistics', 'probability', 'ratio'];
      let topic = 'Algebra'; // default
      
      for (const t of topics) {
        if (query.toLowerCase().includes(t)) {
          topic = t.charAt(0).toUpperCase() + t.slice(1);
          break;
        }
      }
      
      // Generate questions directly without InterpretLambda
      const questions = await this.generateQuestions({
        topic,
        tier,
        count,
        specification_version: 'latest',
        enriched_prompt: query, // Pass full query as enriched prompt
      });
      
      return questions;
    } catch (error) {
      throw error;
    }
  }

  // Session History methods
  async getSessionHistory(limit: number = 50, lastEvaluatedKey?: any): Promise<SessionHistoryResponse> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      const params = new URLSearchParams();
      params.append('limit', limit.toString());
      
      if (lastEvaluatedKey) {
        params.append('last_evaluated_key', JSON.stringify(lastEvaluatedKey));
      }
      
      const response = await this.client.get<SessionHistoryResponse>(`/user/sessions?${params.toString()}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getSessionDetails(sessionId: string): Promise<SessionDetails> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      const response = await this.client.get<SessionDetails>(`/user/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getSessionStatistics(): Promise<SessionStatistics> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      const response = await this.client.get<SessionStatistics>('/user/statistics');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Topic Coverage methods
  async getTopicCoverage(days: number = 30): Promise<any> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      const response = await this.client.get(`/user/coverage?days=${days}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getTopicSuggestions(days: number = 30, maxSuggestions: number = 5): Promise<any> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      const response = await this.client.get(`/user/suggestions?days=${days}&max_suggestions=${maxSuggestions}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Feedback methods
  async submitFeedback(questionId: string, helpful: boolean, difficultyRating: number, comments?: string): Promise<any> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      // Feedback lambda expects flat structure, not nested
      const request = {
        question_id: questionId,
        helpful,
        difficulty_rating: difficultyRating,
        comments: comments || ''
      };
      
      const response = await this.client.post('/feedback', request);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Export methods
  async exportSessionToPDF(sessionId: string): Promise<{ filename: string; pdfData: string }> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      const request = {
        session_id: sessionId,
        user_id: this.authState.user?.username,
        session_token: this.authState.sessionToken,
        format: 'pdf'
      };
      
      const response = await this.client.post('/user/export', request);
      
      if (response.data.success) {
        return {
          filename: response.data.filename,
          pdfData: response.data.pdf_data
        };
      } else {
        throw new Error(response.data.error || 'Export failed');
      }
    } catch (error) {
      console.error('Export error:', error);
      throw error;
    }
  }

  // Generic GET method for flexibility
  async get(url: string, config?: any): Promise<any> {
    return this.client.get(url, config);
  }

  // Generic POST method for flexibility
  async post(url: string, data?: any, config?: any): Promise<any> {
    return this.client.post(url, data, config);
  }
}

// Export a singleton instance
export const apiClient = new ApiClient();
export default apiClient;