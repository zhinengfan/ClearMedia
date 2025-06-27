import { useState, useRef, useEffect } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '../ui/badge';
import type { BadgeVariant } from '../ui/badge';
import { FILE_STATUSES } from '@/constants/statuses';

interface StatusFilterProps {
  selectedStatuses: string[];
  onStatusChange: (statuses: string[]) => void;
  className?: string;
}

export function StatusFilter({
  selectedStatuses,
  onStatusChange,
  className,
}: StatusFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉框
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleStatusToggle = (status: string) => {
    const newStatuses = selectedStatuses.includes(status)
      ? selectedStatuses.filter((s) => s !== status)
      : [...selectedStatuses, status];
    onStatusChange(newStatuses);
  };

  const clearAll = () => {
    onStatusChange([]);
  };

  const selectedCount = selectedStatuses.length;
  const hasSelection = selectedCount > 0;

  return (
    <div className={cn('relative', className)} ref={dropdownRef}>
      {/* 触发按钮 */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background',
          'hover:bg-accent hover:text-accent-foreground',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          isOpen && 'ring-2 ring-ring ring-offset-2'
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">状态筛选</span>
          {hasSelection && (
            <Badge variant="secondary" className="text-xs">
              {selectedCount}
            </Badge>
          )}
        </div>
        <ChevronDown
          className={cn('h-4 w-4 transition-transform', isOpen && 'rotate-180')}
        />
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div className="absolute top-full z-50 mt-1 w-full min-w-[280px] rounded-md border border-input bg-popover p-1 shadow-md">
          <div className="flex items-center justify-between border-b border-border p-2">
            <span className="text-sm font-medium">选择状态</span>
            {hasSelection && (
              <button
                type="button"
                onClick={clearAll}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                清除全部
              </button>
            )}
          </div>
          <div className="max-h-60 overflow-y-auto">
            {FILE_STATUSES.map((status) => {
              const isSelected = selectedStatuses.includes(status.value);
              return (
                <div
                  key={status.value}
                  onClick={() => handleStatusToggle(status.value)}
                  className={cn(
                    'flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2.5 text-sm',
                    'hover:bg-accent hover:text-accent-foreground',
                    isSelected && 'bg-accent text-accent-foreground'
                  )}
                  role="option"
                  aria-selected={isSelected}
                >
                  <div
                    className={cn(
                      'flex h-4 w-4 items-center justify-center rounded border',
                      isSelected
                        ? 'bg-primary border-primary text-primary-foreground'
                        : 'border-input'
                    )}
                  >
                    {isSelected && <Check className="h-3 w-3" />}
                  </div>
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <Badge
                      variant={status.color as BadgeVariant}
                      className="text-xs flex-shrink-0"
                    >
                      {status.label}
                    </Badge>
                    <span className="text-muted-foreground text-xs truncate">
                      {status.value}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
