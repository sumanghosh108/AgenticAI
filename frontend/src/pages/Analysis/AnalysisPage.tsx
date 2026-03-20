import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle, XCircle, ArrowRight, Star, MessageSquare, Bot, Clock } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { ProgressBar } from '@/components/common/ProgressBar';
import { StatusBadge } from '@/components/common/StatusBadge';
import { useTaskProgress } from '@/hooks/useTaskProgress';
import { decisionApi, feedbackApi, reportHistoryApi } from '@/api/client';
import type { AgentInfo } from '@/types';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '@/context/AuthContext';

const STEP_LABELS: Record<string, string> = {
  decompose_task: 'Decomposing query into sub-tasks',
  dispatch_agents: 'Agents researching & analyzing',
  generate_decision: 'Generating structured decision',
  critique_output: 'Multi-critic quality evaluation',
  refine_output: 'Refining based on critique',
  extract_kpis: 'Extracting key performance indicators',
  score_sources: 'Scoring source credibility',
  format_report: 'Generating enterprise report',
  starting: 'Initializing pipeline...',
  completed: 'Analysis complete',
};

const STEP_ORDER = [
  'decompose_task',
  'dispatch_agents',
  'generate_decision',
  'critique_output',
  'extract_kpis',
  'score_sources',
  'format_report',
];

function AgentStatusIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle className="w-4 h-4 text-emerald-500" />;
  if (status === 'failed') return <XCircle className="w-4 h-4 text-red-500" />;
  if (status === 'running') return <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />;
  return <Clock className="w-4 h-4 text-gray-400" />;
}

function AgentCard({ agent }: { agent: AgentInfo }) {
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
        agent.status === 'running'
          ? 'border-brand-300 dark:border-brand-700 bg-brand-50/50 dark:bg-brand-950/30 shadow-sm'
          : agent.status === 'completed'
          ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50/30 dark:bg-emerald-950/20'
          : agent.status === 'failed'
          ? 'border-red-200 dark:border-red-800 bg-red-50/30 dark:bg-red-950/20'
          : 'border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50'
      }`}
    >
      <div className="mt-0.5">
        <AgentStatusIcon status={agent.status} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold truncate">{agent.name}</span>
          <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
            agent.status === 'running'
              ? 'bg-brand-100 text-brand-700 dark:bg-brand-900 dark:text-brand-300'
              : agent.status === 'completed'
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
              : agent.status === 'failed'
              ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
              : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
          }`}>
            {agent.status}
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">{agent.task}</p>
      </div>
    </div>
  );
}

export function AnalysisPage() {
  const [params] = useSearchParams();
  const taskId = params.get('task_id');
  const navigate = useNavigate();
  const { user } = useAuth();
  const progress = useTaskProgress(taskId);

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [feedbackSent, setFeedbackSent] = useState(false);

  // Fetch result when complete
  useEffect(() => {
    if (progress.isComplete && taskId && progress.status === 'completed' && !result) {
      decisionApi.getResult(taskId).then((r) => {
        if (r.success) {
          setResult(r as Record<string, unknown>);
          
          // Auto-save to database so it shows on Dashboard
          if (user?.username && progress.query) {
             reportHistoryApi.saveReport({
               user_name: user.username,
               research_topic: progress.query,
               research_domain: progress.domain || 'general',
               document: (r.final_output as string) || 'Report generated. Content missing.',
             }).catch(() => {
               console.error('Failed to auto-save report');
             });
          }
        }
      });
    }
  }, [progress.isComplete, progress.status, taskId, progress.query, progress.domain, user?.username, result]);

  const submitFeedback = async () => {
    if (!taskId || rating === 0) return;
    await feedbackApi.submit(taskId, rating, feedback);
    setFeedbackSent(true);
  };

  if (!taskId) {
    return (
      <div>
        <Header title="Analysis" subtitle="No task selected" />
        <div className="px-8 py-12 text-center">
          <p className="text-gray-500 mb-4">Start a new analysis from the dashboard.</p>
          <Button onClick={() => navigate('/dashboard')}>Go to Dashboard</Button>
        </div>
      </div>
    );
  }

  const currentStepIdx = STEP_ORDER.indexOf(progress.step);

  return (
    <div>
      <Header title="Decision Analysis" subtitle={`Task: ${taskId}`} />

      <div className="px-8 py-6 space-y-6">
        {/* Overall Progress Card */}
        <Card>
          <div className="flex items-center gap-4 mb-4">
            {progress.isRunning && <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />}
            {progress.status === 'completed' && <CheckCircle className="w-6 h-6 text-emerald-500" />}
            {progress.status === 'failed' && <XCircle className="w-6 h-6 text-red-500" />}
            <div className="flex-1">
              <h2 className="text-lg font-semibold">
                {STEP_LABELS[progress.step] || progress.step || 'Waiting...'}
              </h2>
              <StatusBadge status={progress.status} className="mt-1" />
            </div>
            {progress.isRunning && (
              <span className="text-2xl font-bold text-brand-600 dark:text-brand-400 tabular-nums">
                {Math.round(progress.progress)}%
              </span>
            )}
          </div>

          <ProgressBar value={progress.progress} size="lg" />

          {progress.error && (
            <div className="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400 text-sm">
              {progress.error}
            </div>
          )}

          {/* Step Pipeline */}
          <div className="mt-6 flex flex-wrap gap-2">
            {STEP_ORDER.map((key, idx) => {
              const label = STEP_LABELS[key] || key;
              const isDone = idx < currentStepIdx || progress.status === 'completed';
              const isCurrent = key === progress.step && progress.isRunning;

              return (
                <div
                  key={key}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 transition-all ${
                    isDone
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                      : isCurrent
                      ? 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300 ring-2 ring-brand-300'
                      : 'bg-gray-100 text-gray-400 dark:bg-gray-800'
                  }`}
                >
                  {isDone && <CheckCircle className="w-3 h-3" />}
                  {isCurrent && <Loader2 className="w-3 h-3 animate-spin" />}
                  {label.split(' ').slice(0, 3).join(' ')}
                </div>
              );
            })}
          </div>
        </Card>

        {/* Agent Activity Panel */}
        {progress.totalAgents > 0 && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-brand-100 dark:bg-brand-900 rounded-lg flex items-center justify-center">
                  <Bot className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold">Agent Activity</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {progress.completedAgents} of {progress.totalAgents} agents completed
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {/* Agent count badges */}
                <div className="flex items-center gap-1.5 text-xs">
                  {progress.agents.filter(a => a.status === 'running').length > 0 && (
                    <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 font-medium">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      {progress.agents.filter(a => a.status === 'running').length} active
                    </span>
                  )}
                  {progress.completedAgents > 0 && (
                    <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 font-medium">
                      <CheckCircle className="w-3 h-3" />
                      {progress.completedAgents} done
                    </span>
                  )}
                  {progress.agents.filter(a => a.status === 'pending').length > 0 && (
                    <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 font-medium">
                      <Clock className="w-3 h-3" />
                      {progress.agents.filter(a => a.status === 'pending').length} queued
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Agent progress bar */}
            <div className="mb-4">
              <div className="flex gap-1 h-2 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-800">
                {progress.agents.map((agent) => (
                  <div
                    key={agent.id}
                    className={`flex-1 transition-all duration-500 ${
                      agent.status === 'completed'
                        ? 'bg-emerald-500'
                        : agent.status === 'running'
                        ? 'bg-brand-500 animate-pulse'
                        : agent.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-gray-300 dark:bg-gray-700'
                    }`}
                    title={`${agent.name}: ${agent.status}`}
                  />
                ))}
              </div>
            </div>

            {/* Agent cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {progress.agents.map((agent) => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          </Card>
        )}

        {/* Result */}
        {result && (result.final_output || result.status === 'completed') && (
          <Card title="Analysis Report">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{(result.final_output as string) || 'Report generated. Check downloads.'}</ReactMarkdown>
            </div>

            <div className="flex gap-3 mt-6">
              <Button onClick={() => navigate('/reports')} icon={<ArrowRight className="w-4 h-4" />}>
                View Full Report
              </Button>
            </div>
          </Card>
        )}

        {/* Feedback */}
        {progress.isComplete && progress.status === 'completed' && (
          <Card title="Rate This Analysis" subtitle="Your feedback improves future results">
            {feedbackSent ? (
              <div className="flex items-center gap-2 text-emerald-600">
                <CheckCircle className="w-5 h-5" />
                <span>Thank you for your feedback!</span>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      onClick={() => setRating(n)}
                      className="p-1 transition-transform hover:scale-110"
                    >
                      <Star
                        className={`w-8 h-8 ${
                          n <= rating
                            ? 'text-amber-400 fill-amber-400'
                            : 'text-gray-300 dark:text-gray-600'
                        }`}
                      />
                    </button>
                  ))}
                  {rating > 0 && (
                    <span className="text-sm text-gray-500 ml-2">{rating}/5</span>
                  )}
                </div>

                <div>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Optional: tell us what could be better..."
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition resize-none"
                    rows={3}
                  />
                </div>

                <Button
                  onClick={submitFeedback}
                  disabled={rating === 0}
                  icon={<MessageSquare className="w-4 h-4" />}
                >
                  Submit Feedback
                </Button>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
