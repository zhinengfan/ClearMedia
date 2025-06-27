import { RefreshCw, X, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { MediaFileItem } from '@/lib/api';

interface BatchActionsProps {
  selectedFiles: MediaFileItem[];
  onBatchRetry: () => Promise<void>;
  onBatchDelete?: () => Promise<void>;
  onClearSelection: () => void;
  loading?: boolean;
}

export function BatchActions({
  selectedFiles,
  onBatchRetry,
  onBatchDelete,
  onClearSelection,
  loading = false,
}: BatchActionsProps) {
  if (selectedFiles.length === 0) return null;

  // 计算可重试的文件数量
  const retryableFiles = selectedFiles.filter((file) =>
    ['FAILED', 'CONFLICT', 'NO_MATCH'].includes(file.status)
  );

  // 按状态分组统计
  const statusCounts = selectedFiles.reduce(
    (acc, file) => {
      acc[file.status] = (acc[file.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 transition-all duration-200">
      <div className="flex flex-col gap-3">
        {/* 选择状态信息 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-blue-800">
              已选择 {selectedFiles.length} 个文件
            </span>
            <div className="flex gap-1">
              {Object.entries(statusCounts).map(([status, count]) => {
                const getStatusColor = (status: string) => {
                  switch (status) {
                    case 'COMPLETED':
                      return 'bg-green-100 text-green-700';
                    case 'PROCESSING':
                      return 'bg-purple-100 text-purple-700';
                    case 'PENDING':
                      return 'bg-yellow-100 text-yellow-700';
                    case 'QUEUED':
                      return 'bg-blue-100 text-blue-700';
                    case 'FAILED':
                      return 'bg-red-100 text-red-700';
                    case 'CONFLICT':
                      return 'bg-orange-100 text-orange-700';
                    case 'NO_MATCH':
                      return 'bg-gray-100 text-gray-700';
                    default:
                      return 'bg-gray-100 text-gray-700';
                  }
                };

                return (
                  <Badge
                    key={status}
                    variant="secondary"
                    className={`text-xs ${getStatusColor(status)}`}
                  >
                    {status}: {count}
                  </Badge>
                );
              })}
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClearSelection}
            disabled={loading}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">取消选择</span>
          </Button>
        </div>

        {/* 批量操作按钮 */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onBatchRetry}
            disabled={retryableFiles.length === 0 || loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            批量重试
            {retryableFiles.length > 0 && (
              <Badge variant="secondary" className="ml-1">
                {retryableFiles.length}
              </Badge>
            )}
          </Button>

          {onBatchDelete && (
            <Button
              variant="outline"
              size="sm"
              onClick={onBatchDelete}
              disabled={loading}
              className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="h-4 w-4" />
              批量删除
            </Button>
          )}

          <div className="flex-1" />

          <Button
            variant="ghost"
            size="sm"
            onClick={onClearSelection}
            disabled={loading}
            className="text-blue-600 hover:text-blue-700"
          >
            取消选择
          </Button>
        </div>

        {/* 提示信息 */}
        {retryableFiles.length === 0 && selectedFiles.length > 0 && (
          <div className="text-xs text-blue-600 bg-blue-100 rounded px-2 py-1">
            当前选择的文件中没有可重试的文件（只有失败、冲突或无匹配状态的文件可以重试）
          </div>
        )}
      </div>
    </div>
  );
}
