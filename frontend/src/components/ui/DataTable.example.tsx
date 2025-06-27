import React from 'react';
import { DataTable, type ColumnDef } from './DataTable';
import { type components } from '../../types/openapi';

// 使用 OpenAPI 生成的类型
type MediaFileItem = components['schemas']['MediaFileItem'];

// 示例：为 MediaFileItem 定义列
const mediaFileColumns: ColumnDef<MediaFileItem>[] = [
  {
    id: 'id',
    header: 'ID',
    accessorKey: 'id',
    className: 'w-[80px]',
  },
  {
    id: 'original_filename',
    header: '文件名',
    accessorKey: 'original_filename',
    sortable: true,
    className: 'font-medium',
  },
  {
    id: 'status',
    header: '状态',
    accessorKey: 'status',
    sortable: true,
    cell: (item) => {
      const statusColors: Record<string, string> = {
        PENDING: 'bg-yellow-100 text-yellow-800',
        QUEUED: 'bg-blue-100 text-blue-800',
        PROCESSING: 'bg-purple-100 text-purple-800',
        COMPLETED: 'bg-green-100 text-green-800',
        FAILED: 'bg-red-100 text-red-800',
        CONFLICT: 'bg-orange-100 text-orange-800',
        NO_MATCH: 'bg-gray-100 text-gray-800',
      };

      const colorClass =
        statusColors[item.status] || 'bg-gray-100 text-gray-800';

      return (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
        >
          {item.status}
        </span>
      );
    },
  },
  {
    id: 'created_at',
    header: '创建时间',
    accessorKey: 'created_at',
    sortable: true,
    cell: (item) => {
      return new Date(item.created_at).toLocaleString('zh-CN');
    },
  },
  {
    id: 'updated_at',
    header: '更新时间',
    accessorKey: 'updated_at',
    sortable: true,
    cell: (item) => {
      return new Date(item.updated_at).toLocaleString('zh-CN');
    },
  },
];

// 示例组件
export function MediaFileTableExample() {
  // 模拟数据
  const mockData: MediaFileItem[] = [
    {
      id: 1,
      inode: 1001,
      device_id: 2001,
      original_filepath: '/media/movie1.mp4',
      original_filename: 'movie1.mp4',
      file_size: 1000000,
      status: 'COMPLETED',
      created_at: '2025-01-01T10:00:00Z',
      updated_at: '2025-01-01T10:30:00Z',
    },
    {
      id: 2,
      inode: 1002,
      device_id: 2001,
      original_filepath: '/media/series_s01e01.mkv',
      original_filename: 'series_s01e01.mkv',
      file_size: 2000000,
      status: 'PROCESSING',
      created_at: '2025-01-01T11:00:00Z',
      updated_at: '2025-01-01T11:15:00Z',
    },
    {
      id: 3,
      inode: 1003,
      device_id: 2001,
      original_filepath: '/media/unknown_file.avi',
      original_filename: 'unknown_file.avi',
      file_size: 1500000,
      status: 'FAILED',
      created_at: '2025-01-01T12:00:00Z',
      updated_at: '2025-01-01T12:05:00Z',
    },
  ];

  const [loading, setLoading] = React.useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">媒体文件列表</h2>
        <button
          onClick={() => {
            setLoading(true);
            setTimeout(() => setLoading(false), 2000);
          }}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          模拟加载
        </button>
      </div>

      <DataTable
        data={mockData}
        columns={mediaFileColumns}
        loading={loading}
        enablePagination={true}
        pageSizeOptions={[5, 10, 20]}
        emptyContent={
          <div className="text-center py-8">
            <p className="text-muted-foreground">暂无媒体文件</p>
          </div>
        }
      />
    </div>
  );
}

// 类型安全示例：编译时会检查字段是否存在
export function TypeSafetyExample() {
  // 这些列定义中，TypeScript 会为 accessorKey 提供自动补全
  // 并在编译时检查字段是否存在于 MediaFileItem 类型中
  const typeSafeColumns: ColumnDef<MediaFileItem>[] = [
    {
      id: 'id',
      header: 'ID',
      accessorKey: 'id', // ✅ TypeScript 知道这个字段存在
    },
    {
      id: 'filename',
      header: '文件名',
      accessorKey: 'original_filename', // ✅ TypeScript 知道这个字段存在
    },
    // 如果尝试访问不存在的字段，TypeScript 会报错：
    // {
    //   id: 'non_existent',
    //   header: '不存在的字段',
    //   accessorKey: 'non_existent_field', // ❌ TypeScript 错误！
    // },
  ];

  return <DataTable data={[]} columns={typeSafeColumns} />;
}
