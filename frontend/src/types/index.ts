// ─────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────

export interface User {
  username: string;
  email?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface SignupRequest {
  username: string;
  email: string;
  password: string;
  age?: number;
  gender?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  username?: string;
}

// ─────────────────────────────────────────────
// Decision System
// ─────────────────────────────────────────────

export interface DecisionRequest {
  query: string;
  domain: 'finance' | 'healthcare' | 'general';
  max_iterations: number;
}

export interface ScoringDimension {
  name: string;
  score: number;
  reasoning: string;
}

export interface Decision {
  decision: string;
  confidence: number;
  reasons: string[];
  risks: string[];
  scoring: ScoringDimension[];
  alternatives: string[];
}

export interface SourceScore {
  source: string;
  credibility: number;
  domain_authority: string;
  citation_frequency: number;
  reasoning: string;
}

export interface KPI {
  name: string;
  value: string;
  period: string;
  source: string;
  confidence: number;
}

export interface KPIReport {
  entity: string;
  kpis: KPI[];
  summary: string;
}

export interface EnterpriseReport {
  executive_summary: string;
  key_insights: string[];
  risks: string[];
  recommendations: string[];
  kpis?: KPIReport;
  sources: SourceScore[];
  decision?: Decision;
}

// ─────────────────────────────────────────────
// Task & Progress
// ─────────────────────────────────────────────

export type TaskStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TaskInfo {
  task_id: string;
  status: TaskStatus;
  query: string;
  domain: string;
  current_step: string;
  steps_completed: number;
  total_steps: number;
  progress_pct: number;
  created_at: number;
  updated_at: number;
  has_result: boolean;
  error?: string;
  agents?: AgentInfo[];
  total_agents?: number;
  completed_agents?: number;
}

export interface TaskResult {
  thread_id?: string;
  final_output: string;
  status: string;
  decision?: Decision;
}

export interface AgentInfo {
  id: string;
  name: string;
  type: string;
  task: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface WSMessage {
  type: 'connected' | 'progress' | 'completed' | 'error' | 'pong';
  task_id: string;
  step?: string;
  progress_pct?: number;
  status?: string;
  result?: Record<string, unknown>;
  error?: string;
  details?: {
    agents?: AgentInfo[];
    total_agents?: number;
    completed_agents?: number;
  };
  timestamp: number;
}

// ─────────────────────────────────────────────
// Reports (legacy research system)
// ─────────────────────────────────────────────

export interface ReportRequest {
  topic: string;
  max_analysts: number;
}

// ─────────────────────────────────────────────
// Domain Packs
// ─────────────────────────────────────────────

export interface DomainConfig {
  domain: string;
  display_name: string;
  tools: string[];
  metrics: string[];
  scoring_dimensions: string[];
}

// ─────────────────────────────────────────────
// Metrics & Observability
// ─────────────────────────────────────────────

export interface HistogramStats {
  count: number;
  min?: number;
  max?: number;
  avg?: number;
  p50?: number;
  p95?: number;
  p99?: number;
}

export interface SystemMetrics {
  counters: Record<string, number>;
  histograms: Record<string, HistogramStats>;
  gauges: Record<string, number>;
}

export interface MetricsResponse {
  success: boolean;
  metrics: SystemMetrics;
  audit_entries: number;
  task_stats: {
    total_tasks: number;
    by_status: Record<string, number>;
  };
  feedback_stats: {
    total_feedback: number;
    average_rating: number;
    distribution: Record<number, number>;
  };
}

// ─────────────────────────────────────────────
// Feedback
// ─────────────────────────────────────────────

export interface FeedbackSubmission {
  task_id: string;
  rating: number;
  comment: string;
}

// ─────────────────────────────────────────────
// API Response Wrapper
// ─────────────────────────────────────────────

export interface ApiResponse<T = Record<string, unknown>> {
  success: boolean;
  message?: string;
  errors?: string[];
  [key: string]: unknown;
}
