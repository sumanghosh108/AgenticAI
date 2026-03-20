import { useState, useEffect, type ReactNode } from 'react';
import { RefreshCw, Activity, Zap, AlertTriangle, ThumbsUp } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { decisionApi } from '@/api/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export function MetricsPage() {
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const res = await decisionApi.getMetrics();
      if (res.success) setMetrics(res as Record<string, unknown>);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const taskStats = (metrics?.task_stats as Record<string, unknown>) || {};
  const byStatus = (taskStats.by_status as Record<string, number>) || {};
  const feedbackStats = (metrics?.feedback_stats as Record<string, unknown>) || {};
  const distribution = (feedbackStats.distribution as Record<number, number>) || {};

  const taskChartData = Object.entries(byStatus).map(([status, count]) => ({
    name: status,
    count,
  }));

  const feedbackChartData = Object.entries(distribution).map(([rating, count]) => ({
    name: `${rating} Star`,
    value: count as number,
  }));

  return (
    <div>
      <Header title="System Metrics" subtitle="Observability dashboard for the decision platform" />

      <div className="px-8 py-6 space-y-6">
        {/* Refresh */}
        <div className="flex justify-end">
          <Button variant="secondary" size="sm" onClick={fetchMetrics} loading={loading} icon={<RefreshCw className="w-4 h-4" />}>
            Refresh
          </Button>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            icon={<Activity className="w-5 h-5" />}
            label="Total Tasks"
            value={String((taskStats.total_tasks as number) || 0)}
            color="text-brand-500 bg-brand-50 dark:bg-brand-950"
          />
          <KPICard
            icon={<Zap className="w-5 h-5" />}
            label="Completed"
            value={String((byStatus.completed as number) || 0)}
            color="text-emerald-500 bg-emerald-50 dark:bg-emerald-950"
          />
          <KPICard
            icon={<AlertTriangle className="w-5 h-5" />}
            label="Failed"
            value={String((byStatus.failed as number) || 0)}
            color="text-red-500 bg-red-50 dark:bg-red-950"
          />
          <KPICard
            icon={<ThumbsUp className="w-5 h-5" />}
            label="Avg Rating"
            value={`${(feedbackStats.average_rating as number) || 0}/5`}
            color="text-amber-500 bg-amber-50 dark:bg-amber-950"
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Task Distribution */}
          <Card title="Tasks by Status">
            {taskChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={taskChartData}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {taskChartData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400 text-sm py-8 text-center">No task data yet</p>
            )}
          </Card>

          {/* Feedback Distribution */}
          <Card title="Feedback Ratings">
            {feedbackChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={feedbackChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {feedbackChartData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400 text-sm py-8 text-center">No feedback data yet</p>
            )}
          </Card>
        </div>


      </div>
    </div>
  );
}

function KPICard({ icon, label, value, color }: { icon: ReactNode; label: string; value: string; color: string }): JSX.Element {
  return (
    <Card>
      <div className="flex items-center gap-4">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${color}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </Card>
  );
}
