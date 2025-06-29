import { useState, useEffect } from 'react';
import { useNavigate } from '@tanstack/react-router';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { BadgeVariant } from '@/components/ui/badge';
import { getFiles } from '@/lib/api';
import type { components } from '@/types/openapi';

// 从生成的类型中提取文件列表项的正确类型
type FileItem = components['schemas']['MediaFileItem'];
type FilesApiResponse = components['schemas']['MediaFilesResponse'];

// 状态颜色映射
const getStatusVariant = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'completed';
    case 'PROCESSING':
      return 'processing';
    case 'PENDING':
    case 'QUEUED':
      return 'pending';
    case 'FAILED':
      return 'failed';
    case 'CONFLICT':
      return 'conflict';
    case 'NO_MATCH':
      return 'no-match';
    default:
      return 'default';
  }
};

// 状态文本映射
const getStatusText = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return '已完成';
    case 'PROCESSING':
      return '处理中';
    case 'PENDING':
      return '待处理';
    case 'QUEUED':
      return '排队中';
    case 'FAILED':
      return '失败';
    case 'CONFLICT':
      return '冲突';
    case 'NO_MATCH':
      return '未匹配';
    default:
      return status;
  }
};

// 格式化时间显示
const formatTime = (timeString: string) => {
  try {
    const date = new Date(timeString);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return timeString;
  }
};

export function RecentActivities() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchRecentFiles = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // 获取最近 5 个文件，按更新时间降序排序
        const response = await getFiles({
          skip: 0,
          limit: 5,
          sort: 'created_at:desc',
        });

        // 现在响应是类型安全的
        const data = response as FilesApiResponse;
        setFiles(data.items || []);
      } catch (err) {
        console.error('Failed to fetch recent files:', err);
        setError('获取最近活动失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRecentFiles();
  }, []);

  const handleRowClick = (fileId: number) => {
    navigate({
      to: '/media',
      search: (prev) => ({
        ...prev,
        skip: 0,
        limit: 20,
        status: '',
        search: '',
        sort: 'created_at:desc',
        details: fileId,
      }),
    });
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-secondary-900 mb-4">
          近期活动
        </h2>
        <div className="text-red-500 text-center py-4">{error}</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-secondary-900 mb-4">
        近期活动
      </h2>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>文件名</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>处理时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              // 加载状态
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <div className="h-4 bg-gray-200 rounded animate-pulse" />
                  </TableCell>
                  <TableCell>
                    <div className="h-6 w-16 bg-gray-200 rounded animate-pulse" />
                  </TableCell>
                  <TableCell>
                    <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                  </TableCell>
                </TableRow>
              ))
            ) : files.length === 0 ? (
              // 空状态
              <TableRow>
                <TableCell
                  colSpan={3}
                  className="text-center py-8 text-gray-500"
                >
                  暂无活动记录
                </TableCell>
              </TableRow>
            ) : (
              // 文件列表
              files.map((file) => (
                <TableRow
                  key={file.id}
                  className="cursor-pointer hover:bg-green-50"
                  onClick={() => handleRowClick(file.id)}
                >
                  <TableCell className="font-medium">
                    <div
                      className="truncate max-w-xs"
                      title={file.original_filename}
                    >
                      {file.original_filename}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={getStatusVariant(file.status) as BadgeVariant}
                    >
                      {getStatusText(file.status)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-gray-500">
                    {formatTime(file.created_at)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
