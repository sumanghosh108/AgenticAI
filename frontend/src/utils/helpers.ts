import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function truncate(str: string, len: number): string {
  return str.length > len ? str.slice(0, len) + '...' : str;
}

export function statusColor(status: string): string {
  switch (status) {
    case 'completed': return 'text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950';
    case 'running': return 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-950';
    case 'queued': return 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-950';
    case 'failed': return 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950';
    case 'cancelled': return 'text-gray-500 bg-gray-100 dark:text-gray-400 dark:bg-gray-800';
    default: return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-800';
  }
}

export function domainIcon(domain: string): string {
  switch (domain) {
    case 'finance': return '📊';
    case 'healthcare': return '🏥';
    default: return '🔍';
  }
}
