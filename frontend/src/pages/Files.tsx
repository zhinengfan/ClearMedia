import React from 'react';
import { useSearch, useNavigate } from '@tanstack/react-router';
import { Search, X } from 'lucide-react';
import { Toast } from '../lib/toast';
import { DataTable, type ColumnDef } from '../components/ui/DataTable';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { StatusFilter } from '../components/files/StatusFilter';
import { BatchActions } from '../components/files/BatchActions';
import { useDebounce } from '../hooks/useDebounce';
import {
  getFiles,
  batchRetryFiles,
  type MediaFileItem,
  type GetFilesParams,
} from '../lib/api';
import { FileDetailsSheet } from '../components/files/FileDetailsSheet';

// 搜索参数类型 - 根据实际API支持的参数定义
type FilesSearchParams = {
  skip?: number;
  limit?: number;
  status?: string;
  search?: string;
  sort?: string; // API支持的排序参数
  details?: number; // 文件详情ID
};

// 允许的排序字段（前端UI用）
const VALID_SORT_FIELDS = [
  'created_at',
  'original_filename',
  'status',
  'updated_at',
] as const;
type SortField = (typeof VALID_SORT_FIELDS)[number];

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

// 格式化日期
const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// 定义表格列
const columns: ColumnDef<MediaFileItem>[] = [
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
    className: 'font-medium min-w-[200px]',
  },
  {
    id: 'status',
    header: '状态',
    accessorKey: 'status',
    sortable: true,
    className: 'w-[120px]',
    cell: (item) => (
      <Badge variant={getStatusBadgeVariant(item.status)}>{item.status}</Badge>
    ),
  },
  {
    id: 'created_at',
    header: '创建时间',
    accessorKey: 'created_at',
    sortable: true,
    className: 'w-[160px]',
    cell: (item) => formatDate(item.created_at),
  },
  {
    id: 'updated_at',
    header: '更新时间',
    accessorKey: 'updated_at',
    sortable: true,
    className: 'w-[160px]',
    cell: (item) => formatDate(item.updated_at),
  },
];

export function Files() {
  const search = useSearch({ from: '/media' }) as FilesSearchParams;
  const navigate = useNavigate({ from: '/media' });

  // 状态管理
  const [data, setData] = React.useState<MediaFileItem[]>([]);
  const [total, setTotal] = React.useState(0);
  const [hasNext, setHasNext] = React.useState(false);
  const [hasPrevious, setHasPrevious] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // 选择状态管理
  const [selectedFiles, setSelectedFiles] = React.useState<MediaFileItem[]>([]);
  const [batchLoading, setBatchLoading] = React.useState(false);

  // 搜索框本地状态
  const [searchInput, setSearchInput] = React.useState(search.search || '');

  // 防抖搜索关键词 - 300ms 延迟
  const debouncedSearch = useDebounce(searchInput, 300);

  // 抽取与列表相关的查询参数，忽略 details，避免打开侧滑面板时触发不必要的重新请求
  const {
    skip = 0,
    limit = 20,
    status = '',
    search: keyword = '',
    sort: order = 'created_at:desc',
  } = search;

  // 解析状态参数为数组
  const selectedStatuses = React.useMemo(() => {
    return status ? status.split(',').filter(Boolean) : [];
  }, [status]);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params: GetFilesParams = {
        skip,
        limit,
      };

      // 只有在有值时才添加参数
      if (order) {
        params.sort = order;
      }
      if (status) {
        params.status = status;
      }
      if (keyword) {
        params.search = keyword;
      }

      const response = await getFiles(params);
      setData(response.items);
      setTotal(response.total);
      setHasNext(response.has_next);
      setHasPrevious(response.has_previous);
    } catch (err) {
      console.error('获取文件列表失败:', err);
      setError(err instanceof Error ? err.message : '获取文件列表失败');
    } finally {
      setLoading(false);
    }
  }, [skip, limit, status, keyword, order]);

  // 仅当与列表查询相关的参数发生变化时重新获取数据
  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 同步防抖搜索到URL - 当防抖搜索词变化时更新URL
  React.useEffect(() => {
    if (debouncedSearch !== search.search) {
      navigate({
        search: (prev) => ({
          ...prev,
          search: debouncedSearch,
          skip: 0, // 搜索时重置到第一页
        }),
      });
    }
  }, [debouncedSearch, search.search, navigate]);

  // 同步URL搜索参数到本地输入框状态
  React.useEffect(() => {
    setSearchInput(search.search || '');
  }, [search.search]);

  // 处理分页变化
  const handlePaginationChange = React.useCallback(
    (pagination: { pageIndex: number; pageSize: number }) => {
      navigate({
        search: (prev) => ({
          ...prev,
          skip: pagination.pageIndex * pagination.pageSize,
          limit: pagination.pageSize,
        }),
      });
    },
    [navigate]
  );

  // 处理排序变化
  const handleSortingChange = React.useCallback(
    (sorting: Array<{ id: string; desc: boolean }>) => {
      let sortParam = 'created_at:desc';

      if (sorting.length > 0) {
        const field = sorting[0].id;
        const direction = sorting[0].desc ? 'desc' : 'asc';

        // 验证字段是否有效
        if (VALID_SORT_FIELDS.includes(field as SortField)) {
          sortParam = `${field}:${direction}`;
        }
      }

      navigate({
        search: (prev) => ({
          ...prev,
          sort: sortParam,
        }),
      });
    },
    [navigate]
  );

  // 处理搜索输入变化
  const handleSearchChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchInput(e.target.value);
    },
    []
  );

  // 清除搜索
  const handleSearchClear = React.useCallback(() => {
    setSearchInput('');
  }, []);

  // 移除单个关键词
  const handleKeywordRemove = React.useCallback(
    (keywordToRemove: string) => {
      const nextKeywords = searchInput
        .split(/\s+/)
        .filter((kw) => kw && kw !== keywordToRemove);
      setSearchInput(nextKeywords.join(' '));
    },
    [searchInput]
  );

  // 处理状态筛选变化
  const handleStatusChange = React.useCallback(
    (statuses: string[]) => {
      navigate({
        search: (prev) => ({
          ...prev,
          status: statuses.join(','),
          skip: 0, // 筛选时重置到第一页
        }),
      });
    },
    [navigate]
  );

  // 处理行点击
  const handleRowClick = React.useCallback(
    (item: MediaFileItem) => {
      navigate({
        search: (prev) => ({
          ...prev,
          details: item.id,
        }),
      });
    },
    [navigate]
  );

  // 处理详情面板关闭
  const handleDetailsClose = React.useCallback(() => {
    navigate({
      search: (prev) => ({
        ...prev,
        details: undefined,
      }),
      replace: true,
    });
  }, [navigate]);

  // 处理批量重试
  const handleBatchRetry = React.useCallback(async () => {
    if (selectedFiles.length === 0) return;

    const retryableFiles = selectedFiles.filter((file) =>
      ['FAILED', 'CONFLICT', 'NO_MATCH'].includes(file.status)
    );

    if (retryableFiles.length === 0) {
      Toast.error('当前选择的文件中没有可重试的文件');
      return;
    }

    setBatchLoading(true);
    try {
      const fileIds = retryableFiles.map((file) => file.id);
      const result = await batchRetryFiles(fileIds);

      // 显示结果
      const successCount = result.results.filter((r) => r.success).length;
      const failureCount = result.results.filter((r) => !r.success).length;

      Toast.success(
        `批量重试完成：成功 ${successCount} 个，失败 ${failureCount} 个`
      );

      // 刷新数据
      await fetchData();

      // 清空选择
      setSelectedFiles([]);
    } catch (err) {
      console.error('批量重试失败:', err);
      Toast.error(err instanceof Error ? err.message : '批量重试失败');
    } finally {
      setBatchLoading(false);
    }
  }, [selectedFiles, fetchData]);

  // 清空选择
  const handleClearSelection = React.useCallback(() => {
    setSelectedFiles([]);
  }, []);

  // 判断文件是否可选择（只有失败状态的文件可以被选择进行重试）
  const isFileSelectable = React.useCallback((file: MediaFileItem) => {
    return ['FAILED', 'CONFLICT', 'NO_MATCH', 'PENDING'].includes(file.status);
  }, []);

  // 计算当前分页状态
  const currentPagination = {
    pageIndex: Math.floor(skip / limit),
    pageSize: limit,
  };

  // 计算当前排序状态
  const currentSorting = React.useMemo(() => {
    if (!order) return [];
    const [field, direction] = order.split(':');
    return [{ id: field, desc: direction === 'desc' }];
  }, [order]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">媒体文件管理</h1>
        <p className="text-muted-foreground">管理和查看您的媒体文件处理状态</p>
      </div>

      {/* 搜索和筛选区域 */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
        {/* 搜索框 */}
        <div className="relative flex-1 min-w-0">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索文件名..."
            value={searchInput}
            onChange={handleSearchChange}
            className="pl-9 pr-9"
          />
          {searchInput && (
            <button
              type="button"
              onClick={handleSearchClear}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* 状态筛选器 */}
        <div className="w-full lg:w-[300px] lg:flex-shrink-0">
          <StatusFilter
            selectedStatuses={selectedStatuses}
            onStatusChange={handleStatusChange}
          />
        </div>
      </div>

      {/* 活动筛选器显示 */}
      {(searchInput || selectedStatuses.length > 0) && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">活动筛选器:</span>
          {/* 搜索关键词拆分显示 */}
          {searchInput &&
            searchInput
              .split(/\s+/)
              .filter(Boolean)
              .map((kw) => (
                <Badge key={kw} variant="secondary" className="gap-1">
                  搜索: {kw}
                  <button
                    type="button"
                    onClick={() => handleKeywordRemove(kw)}
                    className="ml-1 hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
          {/* 状态关键词 */}
          {selectedStatuses.map((status) => (
            <Badge key={status} variant="secondary" className="gap-1">
              {status}
              <button
                type="button"
                onClick={() =>
                  handleStatusChange(
                    selectedStatuses.filter((s) => s !== status)
                  )
                }
                className="ml-1 hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {/* 清除全部搜索关键词按钮 */}
          {searchInput && (
            <Badge
              variant="outline"
              className="cursor-pointer gap-1"
              onClick={handleSearchClear}
            >
              清除搜索
              <X className="h-3 w-3" />
            </Badge>
          )}
        </div>
      )}

      {/* 批量操作面板 */}
      <BatchActions
        selectedFiles={selectedFiles}
        onBatchRetry={handleBatchRetry}
        onClearSelection={handleClearSelection}
        loading={batchLoading}
      />

      {error && (
        <div className="rounded-md bg-destructive/15 p-4 text-destructive border border-destructive/20">
          <p className="font-medium">获取数据失败</p>
          <p className="text-sm">{error}</p>
          <button
            onClick={fetchData}
            className="mt-2 text-sm underline hover:no-underline"
          >
            重试
          </button>
        </div>
      )}

      <DataTable
        data={data}
        columns={columns}
        loading={loading}
        pagination={currentPagination}
        onPaginationChange={handlePaginationChange}
        sorting={currentSorting}
        onSortingChange={handleSortingChange}
        enablePagination={true}
        serverSidePagination={true}
        totalItems={total}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
        pageSizeOptions={[10, 20, 50, 100]}
        onRowClick={handleRowClick}
        enableRowSelection={true}
        selectedRecords={selectedFiles}
        onSelectedRecordsChange={setSelectedFiles}
        getRecordId={(record) => String(record.id)}
        isRecordSelectable={isFileSelectable}
        emptyContent={
          <div className="text-center py-12">
            <p className="text-muted-foreground text-lg">暂无媒体文件</p>
            <p className="text-muted-foreground text-sm mt-2">
              上传媒体文件后将在此处显示
            </p>
          </div>
        }
      />

      {/* 文件详情面板 */}
      <FileDetailsSheet
        fileId={search.details || null}
        onClose={handleDetailsClose}
      />

      {!loading && !error && (
        <div className="text-sm text-muted-foreground">
          共找到 {total} 个文件
        </div>
      )}
    </div>
  );
}

export default Files;
