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

  // Combined method for the full workflow - OPTIMIZED for parallel generation
  async generateQuestionsFromQuery(query: string): Promise<QuestionResponse> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      // Parse multi-topic queries: "10 Algebra, 5 Higher Number" or "10 Foundation fractions questions"
      const multiTopicPattern = /(\d+)\s+(?:(Foundation|Higher)\s+)?([^,]+?)(?:\s+questions?)?(?:,|$)/gi;
      const matches = Array.from(query.matchAll(multiTopicPattern));
      
      if (matches.length > 1) {
        // Multiple topics detected - handle each separately and combine
        const allQuestions: any[] = [];
        
        for (const match of matches) {
          const count = parseInt(match[1]);
          const tier = (match[2] || 'Foundation') as 'Foundation' | 'Higher';
          const topicText = match[3].trim();
          
          // Clean up topic name
          const topic = topicText.charAt(0).toUpperCase() + topicText.slice(1).toLowerCase();
          
          // Generate questions for this topic
          const response = await this.generateQuestions({
            topic,
            tier,
            count,
            specification_version: 'latest',
            enriched_prompt: `${count} ${tier} ${topic} questions`,
            force_async: count > 8,
            parallel_processing: true
          });
          
          // Add questions to combined list
          if (response.questions) {
            allQuestions.push(...response.questions);
          }
        }
        
        // Return combined response
        return {
          success: true,
          questions: allQuestions,
          mark_scheme: [], // Will be generated from questions
          session_id: `multi_${Date.now()}`,
          request_id: `multi_${Date.now()}`,
          generated_at: new Date().toISOString(),
          metadata: {
            total_marks: allQuestions.reduce((sum, q) => sum + (q.marks || 0), 0),
            model_version: 'claude-3-haiku',
            generated_at: new Date().toISOString(),
            multi_topic: true,
            topic_count: matches.length
          }
        };
      }
      
      // Single topic query - extract details more flexibly
      const countMatch = query.match(/(\d+)/);
      const count = countMatch ? parseInt(countMatch[1]) : 5;
      
      // Determine tier from query
      let tier: 'Foundation' | 'Higher' = 'Foundation';
      if (query.toLowerCase().includes('higher')) {
        tier = 'Higher';
      }
      
      // Extract topic - be more flexible with topic detection
      // Complete list of ALL Edexcel GCSE topics
      const knownTopics = [
        // Numbers
        'types of numbers', 'place value', 'addition', 'subtraction', 'bidmas', 'bodmas',
        'decimals', 'long division', 'long multiplication', 'prime factors', 'lcm', 'hcf',
        'fractions', 'percentages', 'rounding', 'ordering', 'recurring decimals', 'time',
        'estimating', 'square roots', 'error interval', 'bounds', 'standard form', 'tips',
        // Algebra
        'like terms', 'powers', 'roots', 'indices', 'expanding', 'brackets', 'factorising',
        'surds', 'rationalise', 'expressions', 'equations', 'formulae', 'solving', 'substitution',
        'rearranging', 'quadratics', 'quadratic formula', 'difference of two squares',
        'completing the square', 'algebraic fractions', 'sequences', 'nth term', 'geometric',
        'inequalities', 'iterative', 'simultaneous', 'proof', 'functions', 'composite', 'inverse',
        // Graphs
        'gradients', 'straight line', 'coordinates', 'graphs', 'parallel', 'perpendicular',
        'cubic', 'reciprocal', 'exponential', 'turning points', 'circle graphs', 'tangents',
        'sin', 'cos', 'tan', 'transformations', 'distance-time', 'velocity-time', 'real-life',
        'area under graph', 'line graphs',
        // Ratio
        'ratio', 'proportion', 'direct', 'inverse', 'reverse percentages', 'money',
        'compound growth', 'decay', 'units', 'conversions', 'best buys', 'density', 'mass',
        'volume', 'speed', 'distance', 'pressure', 'force', 'area',
        // Geometry
        'angles', 'geometry', 'corresponding', 'alternate', '2d shapes', 'quadrilaterals',
        'interior', 'exterior', 'symmetry', 'areas', 'circles', 'perimeter', 'circle theorems',
        'sector', 'segments', 'arcs', 'congruent', 'similar', 'enlargements', 'invariant',
        '3d shapes', 'faces', 'edges', 'vertices', 'surface area', 'frustums', 'projections',
        'plans', 'elevations', 'scale drawings', 'loci', 'construction', 'bearings',
        // Trigonometry
        'pythagoras', 'trigonometry', 'sine rule', 'cosine rule', '3d pythagoras', 'vectors',
        'column vectors',
        // Probability
        'probability', 'outcomes', 'product rule', 'frequency trees', 'tree diagrams',
        'conditional probability', 'two-way tables', 'relative frequency', 'venn diagrams',
        'set notation',
        // Statistics
        'types of data', 'mean', 'median', 'mode', 'range', 'sampling', 'pictographs',
        'capture-recapture', 'stem and leaf', 'frequency tables', 'grouped frequency',
        'estimating mean', 'box plots', 'cumulative frequency', 'histograms', 'frequency polygon',
        'bar graphs', 'scatter graphs', 'pie charts',
        // Operations
        'multiplication', 'division', 'multiply', 'divide', 'add', 'subtract'
      ];
      
      let topic = '';
      let enrichedPrompt = query;
      
      // Try to find a known topic
      for (const t of knownTopics) {
        if (query.toLowerCase().includes(t)) {
          topic = t.charAt(0).toUpperCase() + t.slice(1);
          break;
        }
      }
      
      // If no known topic found, extract the main subject from the query
      if (!topic) {
        // Remove numbers, tier words, and common words to find the topic
        const cleanQuery = query
          .replace(/\d+/g, '')
          .replace(/foundation|higher|questions?|only/gi, '')
          .trim();
        
        // Take the first meaningful word as the topic
        const words = cleanQuery.split(/\s+/).filter(w => w.length > 2);
        topic = words[0] ? words[0].charAt(0).toUpperCase() + words[0].slice(1) : 'Algebra';
      }
      
      // For larger requests (>8 questions), force async processing for parallel generation
      const forceAsync = count > 8;
      
      // Generate questions with parallel optimization
      // Pass the full query as enriched_prompt so the AI understands the specific request
      // IMPORTANT: Make the prompt very explicit about the requirements
      let finalPrompt = enrichedPrompt;
      
      // If query contains specific operation keywords, emphasize them
      const operationKeywords = ['addition only', 'subtraction only', 'multiplication only', 'division only', 'only addition', 'only subtraction', 'only multiplication', 'only division'];
      const hasSpecificOperation = operationKeywords.some(keyword => enrichedPrompt.toLowerCase().includes(keyword));
      
      if (hasSpecificOperation) {
        // Extract the operation
        let operation = '';
        if (enrichedPrompt.toLowerCase().includes('addition')) operation = 'addition';
        else if (enrichedPrompt.toLowerCase().includes('subtraction')) operation = 'subtraction';
        else if (enrichedPrompt.toLowerCase().includes('multiplication')) operation = 'multiplication';
        else if (enrichedPrompt.toLowerCase().includes('division')) operation = 'division';
        
        // Make it VERY explicit
        finalPrompt = `${enrichedPrompt}. CRITICAL: ALL questions MUST use ${operation.toUpperCase()} ONLY. Do NOT include any other operations like multiplication, division, subtraction, or addition. ONLY ${operation.toUpperCase()} operations are allowed.`;
      }
      
      const questions = await this.generateQuestions({
        topic,
        tier,
        count,
        specification_version: 'latest',
        enriched_prompt: finalPrompt,
        force_async: forceAsync,
        parallel_processing: true
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

  // Question Retrieval methods
  async retrieveQuestions(
    topic: string,
    grade: 'foundation' | 'higher',
    paperType: 'P1' | 'P2' | 'P3',
    difficultyMin: number = 1,
    difficultyMax: number = 10,
    excludeQuestionIds: string[] = [],
    count: number = 5
  ): Promise<QuestionResponse> {
    if (!this.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    try {
      const request = {
        topic,
        grade,
        paper_type: paperType,
        difficulty_min: difficultyMin,
        difficulty_max: difficultyMax,
        exclude_question_ids: excludeQuestionIds,
        count
      };
      
      const response = await this.client.post('/retrieve-questions', request);
      
      // Transform retrieval response to QuestionResponse format
      if (response.data.questions) {
        return {
          success: true,
          questions: response.data.questions,
          mark_scheme: [], // Will be generated from questions
          session_id: `retrieval_${Date.now()}`,
          request_id: `retrieval_${Date.now()}`,
          generated_at: new Date().toISOString(),
          metadata: {
            ...response.data.metadata,
            source: 'verified_bank',
            model_version: 'verified',
            generated_at: new Date().toISOString()
          }
        };
      }
      
      throw new Error('No questions returned from retrieval');
    } catch (error) {
      // If retrieval fails (empty bank), fall back to generation
      if (error instanceof Error && error.message?.includes('No verified questions available')) {
        console.log('Question bank empty, falling back to generation');
        return this.generateQuestions({
          topic,
          tier: grade === 'foundation' ? 'Foundation' : 'Higher',
          count,
          specification_version: 'latest'
        });
      }
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