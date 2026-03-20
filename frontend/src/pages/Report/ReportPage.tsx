import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileText, Download, Search } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { decisionApi } from '@/api/client';
import ReactMarkdown from 'react-markdown';

export function ReportPage() {
  const [params] = useSearchParams();
  const [threadId, setThreadId] = useState(params.get('thread_id') || '');
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchReport = async () => {
    if (!threadId.trim()) return;
    setLoading(true);
    setError('');

    try {
      const res = await decisionApi.getResult(threadId);
      if (res.success && res.final_output) {
        setReport(res.final_output as string);
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

      <div className="px-8 py-6 space-y-6">
        {/* Search */}
        <Card>
          <div className="flex gap-3">
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

          {error && (
            <p className="mt-3 text-sm text-red-500">{error}</p>
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
