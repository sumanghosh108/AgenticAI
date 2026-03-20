import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, TrendingUp, Stethoscope, Sparkles, Clock, ArrowRight, FileText } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { StatusBadge } from '@/components/common/StatusBadge';
import { decisionApi, healthApi, reportHistoryApi } from '@/api/client';
import { formatTimestamp, truncate } from '@/utils/helpers';
import { useAuth } from '@/context/AuthContext';

const DOMAINS = [
  { id: 'general', label: 'General Research', icon: Search, color: 'bg-blue-500', desc: 'Multi-source web research and analysis' },
  { id: 'finance', label: 'Financial Analysis', icon: TrendingUp, color: 'bg-emerald-500', desc: 'Market data, KPIs, investment decisions' },
  { id: 'healthcare', label: 'Healthcare & Biotech', icon: Stethoscope, color: 'bg-purple-500', desc: 'Clinical research, regulatory analysis' },
];

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('general');
  const [loading, setLoading] = useState(false);
  const [recentTasks, setRecentTasks] = useState<Record<string, unknown>[]>([]);
  const [serverHealth, setServerHealth] = useState<{ status: string; version: string } | null>(null);
  const [pastReports, setPastReports] = useState<Array<{
    id: number;
    user_name: string;
    research_topic: string;
    research_domain: string;
    document: string;
    created_at: string;
  }>>([]);
  const [selectedReport, setSelectedReport] = useState<string | null>(null);

  useEffect(() => {
    healthApi.check().then(setServerHealth).catch(() => {});
    decisionApi.listTasks().then((r) => {
      if (r.success) setRecentTasks(r.tasks.slice(0, 5));
    }).catch(() => {});

    // Fetch previous reports for the logged-in user
    if (user?.username) {
      reportHistoryApi.getReports(user.username).then((r) => {
        if (r.success) setPastReports(r.reports);
      }).catch(() => {});
    }
  }, [user?.username]);

  const handleAnalyze = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await decisionApi.analyzeAsync(query, domain);
      if (res.success && res.task_id) {
        navigate(`/analysis?task_id=${res.task_id}`);
      }
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Header
        title={`Welcome back, ${user?.username || 'Analyst'}`}
        subtitle="Launch a new analysis or review past decisions"
      />

      <div className="px-4 md:px-8 py-4 md:py-6 space-y-6 md:space-y-8">
        {/* Analysis Launcher */}
        <Card className="bg-gradient-to-br from-brand-600 to-brand-800 border-0 text-white">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold mb-1">New Decision Analysis</h2>
              <p className="text-brand-100 text-sm mb-4">
                Enter your research question and select a domain for AI-powered analysis
              </p>

              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., Analyze the AI startup market opportunity in 2025..."
                  className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-brand-200 focus:bg-white/20 focus:border-white/40 outline-none transition"
                  onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                />
                <Button
                  onClick={handleAnalyze}
                  loading={loading}
                  className="bg-white text-brand-700 hover:bg-brand-50"
                  size="lg"
                  icon={<ArrowRight className="w-5 h-5" />}
                >
                  Analyze
                </Button>
              </div>
            </div>
          </div>
        </Card>

        {/* Domain Selector */}
        <div>
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            Select Domain
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
            {DOMAINS.map((d) => (
              <button
                key={d.id}
                onClick={() => setDomain(d.id)}
                className={`text-left p-4 rounded-xl border-2 transition-all ${
                  domain === d.id
                    ? 'border-brand-500 bg-brand-50 dark:bg-brand-950 shadow-sm'
                    : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 bg-white dark:bg-gray-900'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className={`w-9 h-9 ${d.color} rounded-lg flex items-center justify-center`}>
                    <d.icon className="w-5 h-5 text-white" />
                  </div>
                  <span className="font-semibold text-sm">{d.label}</span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">{d.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Recent Tasks & Server Status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Tasks */}
          <Card title="Recent Analyses" className="lg:col-span-2">
            {recentTasks.length === 0 ? (
              <p className="text-gray-400 text-sm py-4">No analyses yet. Launch your first one above.</p>
            ) : (
              <div className="space-y-3">
                {recentTasks.map((task) => (
                  <button
                    key={task.task_id as string}
                    onClick={() => navigate(`/analysis?task_id=${task.task_id}`)}
                    className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      <span className="text-sm truncate">{truncate(task.query as string, 60)}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <StatusBadge status={task.status as string} />
                      <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-brand-500 transition" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Server Status */}
          <Card title="System Status">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">API Server</span>
                <StatusBadge status={serverHealth ? 'completed' : 'failed'} />
              </div>
              {serverHealth && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Version</span>
                    <span className="text-sm font-mono">{serverHealth.version}</span>
                  </div>
                </>
              )}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Active Domain</span>
                <span className="text-sm font-medium capitalize">{domain}</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Previous Reports from Supabase */}
        <Card title="Previous Reports">
          {pastReports.length === 0 ? (
            <p className="text-gray-400 text-sm py-4">No saved reports yet. Generated reports will appear here.</p>
          ) : (
            <div className="space-y-3">
              {pastReports.map((rpt) => (
                <div key={rpt.id} className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
                  <button
                    onClick={() => setSelectedReport(selectedReport === String(rpt.id) ? null : String(rpt.id))}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                  >
                    <div className="flex items-center gap-3 min-w-0 text-left">
                      <FileText className="w-4 h-4 text-brand-500 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{rpt.research_topic}</p>
                        <p className="text-xs text-gray-400">
                          {rpt.research_domain && <span className="capitalize">{rpt.research_domain} · </span>}
                          {new Date(rpt.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <ArrowRight className={`w-4 h-4 text-gray-300 transition-transform ${selectedReport === String(rpt.id) ? 'rotate-90' : ''}`} />
                  </button>
                  {selectedReport === String(rpt.id) && (
                    <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-800">
                      <pre className="mt-3 text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap max-h-64 overflow-y-auto bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                        {rpt.document || 'No document content.'}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
