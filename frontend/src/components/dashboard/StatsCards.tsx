import { useState, useEffect } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getStats } from '@/lib/api';

// 根据后端API实现定义stats响应的类型
interface StatsAPIResponse {
  [key: string]: number | undefined;
  COMPLETED?: number;
  PROCESSING?: number;
  QUEUED?: number;
  PENDING?: number;
  FAILED?: number;
  NO_MATCH?: number;
  CONFLICT?: number;
}

interface StatsData {
  completed: number;
  processing: number;
  pending: number;
  conflict: number;
  failed: number;
  noMatch: number;
  total: number;
}

export function StatsCards() {
  const [stats, setStats] = useState<StatsData>({
    completed: 0,
    processing: 0,
    pending: 0,
    conflict: 0,
    failed: 0,
    noMatch: 0,
    total: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const rawData = await getStats();
        const data = rawData as unknown as StatsAPIResponse;

        // 计算各种状态的统计数据
        const completed = data.COMPLETED || 0;
        const processing = data.PROCESSING || 0; // 只显示正在处理中的
        const pending = (data.PENDING || 0) + (data.QUEUED || 0); // 待处理 = PENDING + QUEUED
        const conflict = data.CONFLICT || 0;
        const failed = data.FAILED || 0;
        const noMatch = data.NO_MATCH || 0;

        const total =
          completed + processing + pending + conflict + failed + noMatch;

        setStats({
          completed,
          processing,
          pending,
          conflict,
          failed,
          noMatch,
          total,
        });
      } catch (err) {
        console.error('Failed to fetch stats:', err);
        setError('获取统计数据失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  // 点击事件处理函数
  const handleCompletedClick = () => {
    navigate({
      to: '/media',
      search: {
        skip: 0,
        limit: 20,
        status: 'COMPLETED',
        search: '',
        sort: 'created_at:desc',
      },
    });
  };

  const handleProcessingClick = () => {
    navigate({
      to: '/media',
      search: {
        skip: 0,
        limit: 20,
        status: 'PROCESSING',
        search: '',
        sort: 'created_at:desc',
      },
    });
  };

  const handlePendingClick = () => {
    navigate({
      to: '/media',
      search: {
        skip: 0,
        limit: 20,
        status: 'PENDING,QUEUED',
        search: '',
        sort: 'created_at:desc',
      },
    });
  };

  const handleConflictClick = () => {
    navigate({
      to: '/media',
      search: {
        skip: 0,
        limit: 20,
        status: 'CONFLICT',
        search: '',
        sort: 'created_at:desc',
      },
    });
  };

  const handleFailedClick = () => {
    navigate({
      to: '/media',
      search: {
        skip: 0,
        limit: 20,
        status: 'FAILED',
        search: '',
        sort: 'created_at:desc',
      },
    });
  };

  const handleNoMatchClick = () => {
    navigate({
      to: '/media',
      search: {
        skip: 0,
        limit: 20,
        status: 'NO_MATCH',
        search: '',
        sort: 'created_at:desc',
      },
    });
  };

  const cards = [
    {
      title: '已完成',
      value: stats.completed,
      className:
        'bg-green-50 border-green-200 hover:bg-green-100 cursor-pointer transition-colors',
      titleClassName: 'text-green-800',
      valueClassName: 'text-green-600',
      onClick: handleCompletedClick,
    },
    {
      title: '处理中',
      value: stats.processing,
      className:
        'bg-blue-50 border-blue-200 hover:bg-blue-100 cursor-pointer transition-colors',
      titleClassName: 'text-blue-800',
      valueClassName: 'text-blue-600',
      onClick: handleProcessingClick,
    },
    {
      title: '待处理',
      value: stats.pending,
      className:
        'bg-yellow-50 border-yellow-200 hover:bg-yellow-100 cursor-pointer transition-colors',
      titleClassName: 'text-yellow-800',
      valueClassName: 'text-yellow-600',
      onClick: handlePendingClick,
    },
    {
      title: '冲突',
      value: stats.conflict,
      className:
        'bg-orange-50 border-orange-200 hover:bg-orange-100 cursor-pointer transition-colors',
      titleClassName: 'text-orange-800',
      valueClassName: 'text-orange-600',
      onClick: handleConflictClick,
    },
    {
      title: '失败',
      value: stats.failed,
      className:
        'bg-red-50 border-red-200 hover:bg-red-100 cursor-pointer transition-colors',
      titleClassName: 'text-red-800',
      valueClassName: 'text-red-600',
      onClick: handleFailedClick,
    },
    {
      title: '未匹配',
      value: stats.noMatch,
      className:
        'bg-purple-50 border-purple-200 hover:bg-purple-100 cursor-pointer transition-colors',
      titleClassName: 'text-purple-800',
      valueClassName: 'text-purple-600',
      onClick: handleNoMatchClick,
    },
    {
      title: '总计',
      value: stats.total,
      className: 'bg-gray-50 border-gray-200 hover:bg-gray-100',
      titleClassName: 'text-gray-800',
      valueClassName: 'text-gray-600',
      onClick: undefined,
    },
  ];

  if (error) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4 mb-6">
        {cards.map((card, index) => (
          <Card key={index} className="bg-red-50 border-red-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-red-800">
                {card.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">--</div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4 mb-6">
      {cards.map((card, index) => (
        <Card key={index} className={card.className} onClick={card.onClick}>
          <CardHeader className="pb-2">
            <CardTitle className={`text-sm font-medium ${card.titleClassName}`}>
              {card.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${card.valueClassName}`}>
              {isLoading ? '...' : card.value.toLocaleString()}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
