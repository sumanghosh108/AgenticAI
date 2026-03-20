import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileText, Download, Search } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { decisionApi, reportHistoryApi } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import ReactMarkdown from 'react-markdown';

export function ReportPage() {
  const [params] = useSearchParams();
  const { user } = useAuth();
  const [threadId, setThreadId] = useState(params.get('thread_id') || '');
  const [topic, setTopic] = useState('');
  const [domain, setDomain] = useState('');
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const fetchReport = async () => {
    if (!threadId.trim()) return;
    setLoading(true);
    setError('');
    setSaved(false);

    try {
      const res = await decisionApi.getResult(threadId);
      if (res.success && res.final_output) {
        const content = res.final_output as string;
        setReport(content);

        // Auto-save to Supabase
        if (user?.username) {
          try {
            await reportHistoryApi.saveReport({
              user_name: user.username,
              research_topic: topic || `Report ${threadId.slice(0, 8)}`,
              research_domain: domain || 'general',
              document: content,
            });
            setSaved(true);
          } catch {
            // Silently fail — report is still displayed
          }
        }
      } else {
        setError('Report not found or not yet completed.');
      }
    } catch {
      setError('Failed to fetch report.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Header title="Reports" subtitle="View and download generated analysis reports" />

      <div className="px-4 md:px-8 py-4 md:py-6 space-y-4 md:space-y-6">
        {/* Search */}
        <Card>
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  value={threadId}
                  onChange={(e) => setThreadId(e.target.value)}
                  placeholder="Enter task ID or thread ID..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition"
                  onKeyDown={(e) => e.key === 'Enter' && fetchReport()}
                />
              </div>
              <Button onClick={fetchReport} loading={loading}>
                Load Report
              </Button>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Research topic (for saving)..."
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition text-sm"
              />
              <input
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="Domain (e.g. finance, healthcare)..."
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none transition text-sm"
              />
            </div>
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-500">{error}</p>
          )}
          {saved && (
            <p className="mt-3 text-sm text-green-500">✓ Report saved to your history</p>
          )}
        </Card>

        {/* Report Content */}
        {report && (
          <Card>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-brand-500" />
                <h2 className="text-lg font-semibold">Analysis Report</h2>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Download className="w-4 h-4" />}
                  onClick={() => {
                    const blob = new Blob([report], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `report_${threadId}.md`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Download .md
                </Button>
              </div>
            </div>

            <div className="prose prose-sm dark:prose-invert max-w-none border-t border-gray-200 dark:border-gray-800 pt-6">
              <ReactMarkdown>{report}</ReactMarkdown>
            </div>
          </Card>
        )}

        {/* Empty State */}
        {!report && !loading && (
          <div className="text-center py-16">
            <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-2">No report loaded</h3>
            <p className="text-sm text-gray-400">Enter a task ID above or run a new analysis from the dashboard.</p>
          </div>
        )}
      </div>
    </div>
  );
}
