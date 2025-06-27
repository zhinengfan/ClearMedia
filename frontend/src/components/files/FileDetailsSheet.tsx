import * as React from 'react';
import { Copy, AlertCircle, RefreshCw, CheckCircle, Clock } from 'lucide-react';
import { Sheet, SheetOverlay, SheetContent } from '../ui/sheet';
import { Badge } from '../ui/badge';
import { getFileDetail, retryFile, type FileDetail } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Toast } from '@/lib/toast';

interface FileDetailsSheetProps {
  fileId: number | null;
  onClose: () => void;
}

// 状态徽章映射
const getStatusBadgeVariant = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'completed';
    case 'PROCESSING':
      return 'processing';
    case 'PENDING':
      return 'pending';
    case 'QUEUED':
      return 'processing';
    case 'FAILED':
      return 'failed';
    case 'CONFLICT':
      return 'conflict';
    case 'NO_MATCH':
      return 'no-match';
    default:
      return 'outline';
  }
};

// 状态图标映射
const getStatusIcon = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    case 'PROCESSING':
    case 'QUEUED':
      return <Clock className="w-4 h-4 text-blue-600" />;
    case 'FAILED':
    case 'CONFLICT':
    case 'NO_MATCH':
      return <AlertCircle className="w-4 h-4 text-red-600" />;
    default:
      return <Clock className="w-4 h-4 text-gray-600" />;
  }
};

// 复制到剪贴板
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('复制失败:', err);
    return false;
  }
};

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化日期
const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

export function FileDetailsSheet({ fileId, onClose }: FileDetailsSheetProps) {
  const [fileDetail, setFileDetail] = React.useState<FileDetail | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [retrying, setRetrying] = React.useState(false);
  const [animationState, setAnimationState] = React.useState<'open' | 'closed'>(
    'closed'
  );

  const isOpen = fileId !== null;

  // 管理动画状态
  React.useEffect(() => {
    if (isOpen) {
      // 延迟一帧以确保动画效果
      const timer = setTimeout(() => setAnimationState('open'), 10);
      return () => clearTimeout(timer);
    } else {
      setAnimationState('closed');
    }
  }, [isOpen]);

  // 获取文件详情
  const fetchFileDetail = React.useCallback(async () => {
    if (!fileId) return;

    setLoading(true);
    setError(null);

    try {
      const detail = await getFileDetail(fileId);
      setFileDetail(detail);
    } catch (err) {
      console.error('获取文件详情失败:', err);
      setError(err instanceof Error ? err.message : '获取文件详情失败');
    } finally {
      setLoading(false);
    }
  }, [fileId]);

  // 当 fileId 变化时获取数据
  React.useEffect(() => {
    if (fileId) {
      fetchFileDetail();
    } else {
      setFileDetail(null);
      setError(null);
    }
  }, [fetchFileDetail, fileId]);

  // 处理重试
  const handleRetry = async () => {
    if (!fileId) return;

    setRetrying(true);
    try {
      await retryFile(fileId);
      // 重试成功后重新获取文件详情
      await fetchFileDetail();
      // 显示成功提示
      Toast.success('文件重试成功，已重新加入处理队列');
    } catch (err) {
      console.error('重试失败:', err);
      // 显示错误提示
      Toast.error(
        err instanceof Error ? err.message : '重试操作失败，请稍后再试'
      );
    } finally {
      setRetrying(false);
    }
  };

  // 处理复制
  const handleCopy = async (text: string, label: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      Toast.success(`${label} 已复制到剪贴板`);
    } else {
      Toast.error('复制失败，请手动复制');
    }
  };

  // 检查是否可以重试
  const canRetry =
    fileDetail &&
    ['FAILED', 'NO_MATCH', 'CONFLICT'].includes(fileDetail.status);

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetOverlay onClick={onClose} state={animationState} />
      <SheetContent size="lg" onClose={onClose} state={animationState}>
        <div className="p-6 h-full overflow-auto">
          {/* 标题区域 */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-2">文件详情</h2>
            {fileDetail && (
              <div className="flex items-center gap-2">
                {getStatusIcon(fileDetail.status)}
                <Badge variant={getStatusBadgeVariant(fileDetail.status)}>
                  {fileDetail.status}
                </Badge>
              </div>
            )}
          </div>

          {/* 加载状态 */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-muted-foreground">加载中...</span>
            </div>
          )}

          {/* 错误状态 */}
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 p-4 mb-6">
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <h3 className="text-sm font-medium text-red-800 mb-1">
                    获取详情失败
                  </h3>
                  <p className="text-sm text-red-700">{error}</p>
                  <button
                    onClick={fetchFileDetail}
                    className="mt-2 text-sm text-red-800 underline hover:no-underline"
                  >
                    重试
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 文件详情内容 */}
          {fileDetail && !loading && (
            <div className="space-y-6">
              {/* 基本信息 */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium">基本信息</h3>

                <div className="grid gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      文件名
                    </label>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-sm font-mono bg-gray-50 p-2 rounded flex-1 break-all">
                        {fileDetail.original_filename}
                      </p>
                      <button
                        onClick={() =>
                          handleCopy(fileDetail.original_filename, '文件名')
                        }
                        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                        title="复制文件名"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      原始路径
                    </label>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-sm font-mono bg-gray-50 p-2 rounded flex-1 break-all">
                        {fileDetail.original_filepath}
                      </p>
                      <button
                        onClick={() =>
                          handleCopy(fileDetail.original_filepath, '原始路径')
                        }
                        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                        title="复制原始路径"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        文件大小
                      </label>
                      <p className="text-sm mt-1">
                        {formatFileSize(fileDetail.file_size)}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        重试次数
                      </label>
                      <p className="text-sm mt-1">{fileDetail.retry_count}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        创建时间
                      </label>
                      <p className="text-sm mt-1">
                        {formatDate(fileDetail.created_at)}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        更新时间
                      </label>
                      <p className="text-sm mt-1">
                        {formatDate(fileDetail.updated_at)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* 处理结果 */}
              {(fileDetail.tmdb_id ||
                fileDetail.media_type ||
                fileDetail.new_filepath) && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">处理结果</h3>

                  <div className="grid gap-4">
                    {fileDetail.tmdb_id && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          TMDB ID
                        </label>
                        <p className="text-sm mt-1">{fileDetail.tmdb_id}</p>
                      </div>
                    )}

                    {fileDetail.media_type && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          媒体类型
                        </label>
                        <p className="text-sm mt-1 capitalize">
                          {fileDetail.media_type}
                        </p>
                      </div>
                    )}

                    {fileDetail.new_filepath && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          新文件路径
                        </label>
                        <div className="flex items-center gap-2 mt-1">
                          <p className="text-sm font-mono bg-green-50 p-2 rounded flex-1 break-all">
                            {fileDetail.new_filepath}
                          </p>
                          <button
                            onClick={() =>
                              handleCopy(fileDetail.new_filepath!, '新文件路径')
                            }
                            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                            title="复制新文件路径"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 错误信息 */}
              {fileDetail.error_message && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">错误信息</h3>
                  <div className="rounded-md bg-red-50 border border-red-200 p-4">
                    <div className="flex items-start">
                      <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
                      <p className="text-sm text-red-700 whitespace-pre-wrap">
                        {fileDetail.error_message}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* 处理数据 */}
              {(fileDetail.llm_guess || fileDetail.processed_data) && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">处理数据</h3>

                  {fileDetail.llm_guess && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        LLM 分析结果
                      </label>
                      <pre className="text-xs mt-1 bg-gray-50 p-3 rounded overflow-auto max-h-40">
                        {JSON.stringify(fileDetail.llm_guess, null, 2)}
                      </pre>
                    </div>
                  )}

                  {fileDetail.processed_data && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        处理后数据
                      </label>
                      <pre className="text-xs mt-1 bg-gray-50 p-3 rounded overflow-auto max-h-40">
                        {JSON.stringify(fileDetail.processed_data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* 操作区域 */}
              {canRetry && (
                <div className="pt-4 border-t">
                  <button
                    onClick={handleRetry}
                    disabled={retrying}
                    className={cn(
                      'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                      'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed'
                    )}
                  >
                    <RefreshCw
                      className={cn('w-4 h-4', retrying && 'animate-spin')}
                    />
                    {retrying ? '重试中...' : '重试处理'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
