import { useState, useEffect } from 'react';
import {
  FileText, Download, Loader2, CheckCircle, FileDown,
  FilePlus, Eye, EyeOff, FileType2, AlertCircle,
} from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { reportHistoryApi, reportFilesApi } from '@/api/client';
import type { ReportFile } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import ReactMarkdown from 'react-markdown';

interface UserReport {
  id: number;
  user_name: string;
  research_topic: string;
  research_domain: string;
  document: string;
  created_at: string;
}

export function ReportPage() {
  const { user } = useAuth();
  const [reports, setReports] = useState<UserReport[]>([]);
  const [reportFiles, setReportFiles] = useState<Record<number, ReportFile[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [error, setError] = useState('');

  // Fetch reports and files on mount
  useEffect(() => {
    if (!user?.username) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [reportsRes, filesRes] = await Promise.all([
          reportHistoryApi.getReports(user.username),
          reportFilesApi.listFiles(user.username),
        ]);

        if (reportsRes.success) {
          setReports(reportsRes.reports);
        }

        if (filesRes.success) {
          // Group files by report_id
          const grouped: Record<number, ReportFile[]> = {};
          for (const f of filesRes.files) {
            if (!grouped[f.report_id]) grouped[f.report_id] = [];
            grouped[f.report_id].push(f);
          }
          setReportFiles(grouped);
        }
      } catch {
        setError('Failed to load reports.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user?.username]);

  const generateFiles = async (reportId: number) => {
    if (!user?.username) return;
    setGeneratingId(reportId);
    setError('');

    try {
      const res = await reportFilesApi.generateFiles(reportId, user.username);
      if (res.success && res.files) {
        // Refresh files for this report
        const filesRes = await reportFilesApi.getFilesForReport(reportId, user.username);
        if (filesRes.success) {
          setReportFiles(prev => ({ ...prev, [reportId]: filesRes.files }));
        }
      } else {
        setError(res.message || 'Failed to generate files');
      }
    } catch {
      setError('Failed to generate files. Check if B2 storage is configured.');
    } finally {
      setGeneratingId(null);
    }
  };

  const downloadFile = async (file: ReportFile) => {
    if (!user?.username) return;
    setDownloadingId(file.id);

    try {
      const res = await reportFilesApi.getDownloadUrl(file.id, user.username);
      if (res.success && res.download_url) {
        // Open in new tab — the authorized URL handles the download
        window.open(res.download_url, '_blank');
      } else {
        setError(res.message || 'Failed to get download link');
      }
    } catch {
      setError('Failed to generate download link.');
    } finally {
      setDownloadingId(null);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (!user?.username) {
    return (
      <div>
        <Header title="Reports" subtitle="View and download generated analysis reports" />
        <div className="px-8 py-16 text-center">
          <p className="text-gray-500">Please log in to view your reports.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Reports" subtitle="View and download your generated analysis reports" />

      <div className="px-4 md:px-8 py-4 md:py-6 space-y-4">
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError('')} className="ml-auto text-xs underline">dismiss</button>
          </div>
        )}

        {loading && (
          <div className="text-center py-16">
            <Loader2 className="w-8 h-8 text-brand-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-500">Loading your reports...</p>
          </div>
        )}

        {!loading && reports.length === 0 && (
          <div className="text-center py-16">
            <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-500 dark:text-gray-400 mb-2">No reports yet</h3>
            <p className="text-sm text-gray-400">Run an analysis from the dashboard to generate your first report.</p>
          </div>
        )}

        {!loading && reports.map((report) => {
          const files = reportFiles[report.id] || [];
          const hasPdf = files.some(f => f.file_type === 'pdf');
          const hasDocx = files.some(f => f.file_type === 'docx');
          const isExpanded = expandedId === report.id;
          const isGenerating = generatingId === report.id;

          return (
            <Card key={report.id} className="overflow-hidden">
              {/* Report Header */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <div className="w-10 h-10 bg-brand-100 dark:bg-brand-900 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                    <FileText className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold truncate">{report.research_topic}</h3>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      {report.research_domain && (
                        <span className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 capitalize">
                          {report.research_domain}
                        </span>
                      )}
                      <span>{new Date(report.created_at).toLocaleDateString('en-US', {
                        year: 'numeric', month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}</span>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Preview toggle */}
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={isExpanded ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    onClick={() => setExpandedId(isExpanded ? null : report.id)}
                  >
                    {isExpanded ? 'Hide' : 'Preview'}
                  </Button>

                  {/* Generate PDF/DOCX if not yet generated */}
                  {(!hasPdf || !hasDocx) && (
                    <Button
                      size="sm"
                      loading={isGenerating}
                      icon={<FilePlus className="w-4 h-4" />}
                      onClick={() => generateFiles(report.id)}
                    >
                      Generate PDF & DOCX
                    </Button>
                  )}
                </div>
              </div>

              {/* Download Buttons (visible when files exist) */}
              {files.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {files.map((file) => (
                    <button
                      key={file.id}
                      onClick={() => downloadFile(file)}
                      disabled={downloadingId === file.id}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition
                        ${file.file_type === 'pdf'
                          ? 'bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-950 dark:hover:bg-red-900 dark:text-red-300 border border-red-200 dark:border-red-800'
                          : 'bg-blue-50 hover:bg-blue-100 text-blue-700 dark:bg-blue-950 dark:hover:bg-blue-900 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                        }
                        disabled:opacity-50`}
                    >
                      {downloadingId === file.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <FileDown className="w-4 h-4" />
                      )}
                      <span>Download {file.file_type.toUpperCase()}</span>
                      <span className="text-xs opacity-60">({formatFileSize(file.file_size)})</span>
                    </button>
                  ))}

                  {/* Also offer raw Markdown download */}
                  <button
                    onClick={() => {
                      const blob = new Blob([report.document], { type: 'text/markdown' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${user.username}_${report.research_topic.slice(0, 30).replace(/\s+/g, '_')}.md`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 transition"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Markdown</span>
                  </button>
                </div>
              )}

              {/* Files info badges */}
              {files.length > 0 && (
                <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
                  <CheckCircle className="w-3 h-3 text-emerald-500" />
                  <span>
                    {files.length} file{files.length > 1 ? 's' : ''} stored securely
                    — authorized download links expire in 1 hour
                  </span>
                </div>
              )}

              {/* Expanded Preview */}
              {isExpanded && report.document && (
                <div className="mt-4 border-t border-gray-200 dark:border-gray-800 pt-4">
                  <div className="prose prose-sm dark:prose-invert max-w-none max-h-96 overflow-y-auto bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                    <ReactMarkdown>{report.document}</ReactMarkdown>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
