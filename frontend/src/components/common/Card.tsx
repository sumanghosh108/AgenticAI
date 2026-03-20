import { cn } from '@/utils/helpers';
import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
  padding?: boolean;
  hover?: boolean;
}

export function Card({ children, title, subtitle, className, padding = true, hover = false }: Props) {
  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm',
        hover && 'hover:shadow-md hover:border-brand-200 dark:hover:border-brand-800 transition-all',
        padding && 'p-6',
        className
      )}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          {title && <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>}
          {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}
