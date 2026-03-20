import { cn } from '@/utils/helpers';

interface Props {
  value: number;
  label?: string;
  showPercent?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function ProgressBar({ value, label, showPercent = true, className, size = 'md' }: Props) {
  const clamped = Math.min(Math.max(value, 0), 100);
  const heights = { sm: 'h-1.5', md: 'h-2.5', lg: 'h-4' };

  return (
    <div className={cn('w-full', className)}>
      {(label || showPercent) && (
        <div className="flex justify-between items-center mb-1">
          {label && <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>}
          {showPercent && <span className="text-sm text-gray-500">{Math.round(clamped)}%</span>}
        </div>
      )}
      <div className={cn('w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden', heights[size])}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            clamped === 100
              ? 'bg-emerald-500'
              : 'bg-brand-500 bg-gradient-to-r from-brand-500 to-brand-400'
          )}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
