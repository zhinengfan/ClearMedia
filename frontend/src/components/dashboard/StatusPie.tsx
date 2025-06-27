import { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';

// 定义状态颜色映射，使用 Tailwind 配色
const STATUS_COLORS = {
  COMPLETED: '#10b981', // green-500
  PROCESSING: '#3b82f6', // blue-500
  PENDING: '#f59e0b', // yellow-500
  QUEUED: '#f59e0b', // yellow-500 (合并到待处理)
  CONFLICT: '#f97316', // orange-500
  FAILED: '#ef4444', // red-500
  NO_MATCH: '#8b5cf6', // purple-500
} as const;

// 状态标签映射
const STATUS_LABELS = {
  COMPLETED: '已完成',
  PROCESSING: '处理中',
  PENDING: '待处理',
  QUEUED: '待处理',
  CONFLICT: '冲突',
  FAILED: '失败',
  NO_MATCH: '未匹配',
} as const;

interface StatusPieProps {
  data: Record<string, number>;
  size?: number;
  className?: string;
}

interface PieDataItem {
  name: string;
  value: number;
  color: string;
  originalStatus: string;
}

export function StatusPie({
  data,
  size = 300,
  className = '',
}: StatusPieProps) {
  // 转换数据格式为图表所需的格式
  const pieData = useMemo((): PieDataItem[] => {
    const result: PieDataItem[] = [];

    // 合并PENDING和QUEUED为"待处理"
    const pendingCount = (data.PENDING || 0) + (data.QUEUED || 0);
    if (pendingCount > 0) {
      result.push({
        name: STATUS_LABELS.PENDING,
        value: pendingCount,
        color: STATUS_COLORS.PENDING,
        originalStatus: 'PENDING',
      });
    }

    // 处理其他状态
    Object.entries(data).forEach(([status, count]) => {
      if (status === 'PENDING' || status === 'QUEUED' || !count) return;

      const statusKey = status as keyof typeof STATUS_COLORS;
      if (STATUS_COLORS[statusKey] && STATUS_LABELS[statusKey]) {
        result.push({
          name: STATUS_LABELS[statusKey],
          value: count,
          color: STATUS_COLORS[statusKey],
          originalStatus: status,
        });
      }
    });

    // 按数量降序排序
    return result.sort((a, b) => b.value - a.value);
  }, [data]);

  interface TooltipPayloadItem {
    payload: PieDataItem;
    color: string;
    value: number;
  }

  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: TooltipPayloadItem[];
  }) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload as PieDataItem;
      return (
        <div className="bg-white p-2 border border-gray-200 rounded shadow-sm">
          <p className="text-sm font-medium" style={{ color: data.color }}>
            {data.name}
          </p>
          <p className="text-sm text-gray-600">
            数量: {data.value.toLocaleString()}
          </p>
        </div>
      );
    }
    return null;
  };

  interface LegendPayloadItem {
    color: string;
    value: string;
    payload: PieDataItem;
  }

  const CustomLegend = ({ payload }: { payload?: LegendPayloadItem[] }) => {
    return (
      <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-2">
        {payload?.map((entry, index) => (
          <li key={index} className="flex items-center text-sm">
            <span
              className="w-3 h-3 rounded-full mr-1.5"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-700">
              {entry.value} ({entry.payload.value})
            </span>
          </li>
        ))}
      </ul>
    );
  };

  // 如果没有数据，显示空状态
  if (pieData.length === 0) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        style={{ height: size }}
      >
        <div className="text-center text-gray-500">
          <div className="text-lg mb-1">📊</div>
          <div className="text-sm">暂无数据</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${className}`} style={{ height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            innerRadius={size * 0.15}
            outerRadius={size * 0.3}
            paddingAngle={2}
            dataKey="value"
          >
            {pieData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} isAnimationActive={false} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
