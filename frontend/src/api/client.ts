/**
 * API Client — centralized HTTP client for all backend communication.
 *
 * - Typed request/response
 * - Automatic error handling
 * - Auth token injection
 * - Base URL configuration
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  // Inject auth token if available
  const token = localStorage.getItem('auth_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      data.message || `Request failed: ${response.status}`,
      response.status,
      data
    );
  }

  return response.json();
}

// ─── Auth ─────────────────────────────────────

export const authApi = {
  login: (username: string, password: string) =>
    request<{ success: boolean; message: string; username?: string }>('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  signup: (data: {
    username: string;
    email: string;
    password: string;
    age?: number;
    gender?: string;
  }) =>
    request<{ success: boolean; message: string }>('/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  googleAuth: (code: string) =>
    request<{ success: boolean; message: string; username?: string }>(
      '/google_auth',
      { method: 'POST', body: JSON.stringify({ code }) }
    ),

  getGoogleAuthUrl: () => 
    request<{ success: boolean; url?: string; message?: string }>('/google_auth_url', { method: 'GET' }),
};

// ─── Decision Workflow ────────────────────────

export const decisionApi = {
  analyze: (query: string, domain: string, max_iterations = 3, username = '') =>
    request<{
      success: boolean;
      thread_id?: string;
      final_output?: string;
      status?: string;
      decision?: Record<string, unknown>;
      message?: string;
      remaining?: number;
      daily_limit?: boolean;
    }>('/decision/analyze', {
      method: 'POST',
      body: JSON.stringify({ query, domain, max_iterations, username }),
    }),

  analyzeAsync: (query: string, domain: string, max_iterations = 3, username = '') =>
    request<{
      success: boolean;
      task_id?: string;
      message?: string;
      remaining?: number;
      daily_limit?: boolean;
    }>(
      '/decision/analyze/async',
      {
        method: 'POST',
        body: JSON.stringify({ query, domain, max_iterations, username }),
      }
    ),

  getUsage: (username: string) =>
    request<{
      success: boolean;
      username: string;
      date: string;
      request_count: number;
      remaining: number;
      limit_reached: boolean;
    }>(`/decision/usage/${username}`),

  getStatus: (taskId: string) =>
    request<{ success: boolean } & Record<string, unknown>>(
      `/decision/status/${taskId}`
    ),

  getResult: (taskId: string) =>
    request<{ success: boolean } & Record<string, unknown>>(
      `/decision/result/${taskId}`
    ),

  cancel: (taskId: string) =>
    request<{ success: boolean; message: string }>(
      `/decision/cancel/${taskId}`,
      { method: 'POST' }
    ),

  listTasks: () =>
    request<{ success: boolean; tasks: Record<string, unknown>[] }>(
      '/decision/tasks'
    ),

  getDomains: () =>
    request<{
      success: boolean;
      domains: Record<string, Record<string, unknown>>;
    }>('/decision/domains'),

  getMetrics: () =>
    request<Record<string, unknown>>('/decision/metrics'),

  getPromptVersions: () =>
    request<{
      success: boolean;
      versions: Record<string, string[]>;
    }>('/decision/prompts'),
};

// ─── Feedback ─────────────────────────────────

export const feedbackApi = {
  submit: (task_id: string, rating: number, comment = '') =>
    request<{ success: boolean; feedback_id?: string }>('/decision/feedback', {
      method: 'POST',
      body: JSON.stringify({ task_id, rating, comment }),
    }),

  getStats: () =>
    request<Record<string, unknown>>('/decision/feedback/stats'),
};

// ─── Reports (Legacy) ─────────────────────────

export const reportApi = {
  generate: (topic: string, max_analysts = 3) =>
    request<{ success: boolean; thread_id?: string }>('/generate_report', {
      method: 'POST',
      body: JSON.stringify({ topic, max_analysts }),
    }),

  submitFeedback: (thread_id: string, feedback: string) =>
    request<{ success: boolean }>('/submit_feedback', {
      method: 'POST',
      body: JSON.stringify({ thread_id, feedback }),
    }),

  getStatus: (threadId: string) =>
    request<Record<string, unknown>>(`/report_status/${threadId}`),
};

// ─── Report History (Supabase) ────────────────

export const reportHistoryApi = {
  saveReport: (data: {
    user_name: string;
    research_topic: string;
    research_domain: string;
    document: string;
  }) =>
    request<{ success: boolean; message: string; report?: Record<string, unknown> }>(
      '/save_report',
      { method: 'POST', body: JSON.stringify(data) }
    ),

  getReports: (username: string) =>
    request<{
      success: boolean;
      reports: Array<{
        id: number;
        user_name: string;
        research_topic: string;
        research_domain: string;
        document: string;
        created_at: string;
      }>;
    }>(`/user_reports/${username}`),
};

// ─── Health ───────────────────────────────────

export const healthApi = {
  check: () => {
    const healthUrl = API_BASE.replace(/\/api$/, '/health');
    return fetch(healthUrl).then((r) => r.json()) as Promise<{
      status: string;
      service: string;
      version: string;
      total_requests_served: number;
    }>;
  },
};

export { ApiError };
