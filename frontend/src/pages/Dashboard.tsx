import { StatsCards } from '@/components/dashboard/StatsCards';
import { StatusPie } from '@/components/dashboard/StatusPie';
import { RecentActivities } from '@/components/dashboard/RecentActivities';
import { useState, useEffect } from 'react';
import { getStats } from '@/lib/api';

export function Dashboard() {
  const [statsData, setStatsData] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setIsLoading(true);
        const data = await getStats();
        setStatsData(data as Record<string, number>);
      } catch (error) {
        console.error('Failed to fetch stats for pie chart:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-secondary-900 mb-6 tracking-tight">
        Dashboard
      </h1>

      {/* 统计卡片 */}
      <StatsCards />

      {/* 状态分布环形图 */}
      <div className="mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-secondary-900 mb-4">
            文件状态分布
          </h2>
          {isLoading ? (
            <div className="flex items-center justify-center h-80">
              <div className="text-gray-500">加载中...</div>
            </div>
          ) : (
            <StatusPie data={statsData} size={320} className="mx-auto" />
          )}
        </div>
      </div>

      {/* 近期活动表格 */}
      <RecentActivities />
    </div>
  );
}

export default Dashboard;
