// API Types based on the design document

export interface QueryIntent {
  topic: string;
  subtopic?: string;
  tier: 'Foundation' | 'Higher';
  count: number;
  marks?: number;
  confidence: number;
  specification_version?: string;
}

export interface Question {
  id: string;
  question_text: string;
  marks: number;
  tier: 'Foundation' | 'Higher';
  topic: string;
  subtopic?: string;
  difficulty_score?: number;
}

export interface MarkScheme {
  question_id: string;
  marking_criteria: string;
  method_marks: number;
  accuracy_marks: number;
}

export interface QuestionResponse {
  success?: boolean;
  questions?: Question[]; // Made optional for async responses
  mark_scheme?: MarkScheme[]; // Made optional for async responses
  session_id?: string;
  request_id?: string;
  generated_at?: string;
  metadata?: {
    generated_at: string;
    model_version: string;
    total_marks: number;
    specification_version?: string;
    completion_status?: 'complete' | 'partial_timeout';
    message?: string;
    async_generation?: boolean;
    job_id?: string;
    generation_time?: number;
  };
  // Async response fields
  async?: boolean;
  job_id?: string;
  status?: 'processing' | 'completed' | 'failed';
  progress?: number;
  estimated_completion_minutes?: number;
  message?: string; // Added for async status messages
  polling_info?: {
    check_status_endpoint: string;
    recommended_poll_interval_seconds: number;
    max_wait_time_minutes: number;
  };
  suggestions?: string[];
}

export interface ApiError {
  error: {
    type: 'ValidationError' | 'TimeoutError' | 'TimeoutWarning' | 'ServiceUnavailable' | 'InternalError' | 'AuthenticationError';
    message: string;
    details?: string;
    request_id: string;
    timestamp: string;
    guidance?: string;
    retry_after?: number;
  };
  suggestions?: string[];
}

export interface InterpretRequest {
  query: string;
  user_id?: string;
  session_token?: string;
}

export interface GenerateRequest {
  topic: string;
  tier: 'Foundation' | 'Higher';
  count: number;
  specification_version?: string;
  user_id?: string;
  session_token?: string;
}

// Authentication Types
export interface AuthRequest {
  action: 'register' | 'login' | 'validate';
  username?: string;
  password?: string;
  email?: string;
  school?: string;
  subject_specialization?: string;
  session_token?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  session_token?: string;
  user_id?: string;
  expires_at?: string;
}

export interface User {
  username: string;
  email: string;
  school?: string;
  subject_specialization?: string;
  created_at?: string;
  last_login?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  sessionToken: string | null;
  expiresAt: Date | null;
}

// Session History Types
export interface SessionMetadata {
  topic: string;
  tier: 'Foundation' | 'Higher';
  question_count: number;
  total_marks: number;
  generation_time?: number;
  specification_version?: string;
  created_at: string;
  request_id: string;
  // Async job fields
  status?: 'processing' | 'completed' | 'failed';
  progress?: number;
  job_id?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface SessionSummary {
  session_id: string;
  query: string;
  timestamp: number;
  question_count: number;
  metadata: SessionMetadata;
}

export interface SessionDetails {
  session_id: string;
  user_id: string;
  query: string;
  generated_questions: Question[];
  timestamp: number;
  ttl: number;
  metadata: SessionMetadata;
}

export interface SessionHistoryResponse {
  sessions: SessionSummary[];
  count: number;
  has_more: boolean;
  last_evaluated_key?: any;
}

export interface SessionStatistics {
  total_sessions: number;
  recent_sessions_7_days: number;
  total_questions_generated: number;
  most_common_topics: Array<{
    topic: string;
    count: number;
  }>;
  average_questions_per_session: number;
}

// Feedback Types
export interface FeedbackRequest {
  question_id: string;
  user_id: string;
  session_token: string;
  feedback: {
    helpful: boolean;
    difficulty_rating: number; // 1-10 scale
    comments?: string;
  };
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
  updated_quality_score?: number;
}