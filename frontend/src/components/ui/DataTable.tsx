import * as React from 'react';
import { cn } from '@/lib/utils';
import { Button } from './button';
import { Checkbox } from './checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './table';
import { usePagination, type PaginationState } from '../../hooks/usePagination';

// 列定义接口
export interface ColumnDef<T extends object> {
  /** 列的唯一标识 */
  id: string;
  /** 列标题 */
  header: string;
  /** 数据访问器函数或属性名 */
  accessorKey?: keyof T;
  /** 自定义单元格渲染函数 */
  cell?: (item: T) => React.ReactNode;
  /** 列是否可排序 */
  sortable?: boolean;
  /** 列的CSS类名 */
  className?: string;
}

// 排序状态接口
export interface SortingState {
  id: string;
  desc: boolean;
}

// DataTable 组件属性
export interface DataTableProps<T extends object> {
  /** 表格数据 */
  data: T[];
  /** 列定义 */
  columns: ColumnDef<T>[];
  /** 是否显示加载状态 */
  loading?: boolean;
  /** 加载状态的骨架行数 */
  skeletonRows?: number;
  /** 分页状态（受控） */
  pagination?: PaginationState;
  /** 分页状态变更回调 */
  onPaginationChange?: (pagination: PaginationState) => void;
  /** 排序状态 */
  sorting?: SortingState[];
  /** 排序状态变更回调 */
  onSortingChange?: (sorting: SortingState[]) => void;
  /** 行点击回调 */
  onRowClick?: (item: T) => void;
  /** 表格类名 */
  className?: string;
  /** 是否启用分页 */
  enablePagination?: boolean;
  /** 分页大小选项 */
  pageSizeOptions?: number[];
  /** 无数据时的显示内容 */
  emptyContent?: React.ReactNode;
  /** 总数据条数（用于服务器端分页） */
  totalItems?: number;
  /** 是否使用服务器端分页（默认false，使用客户端分页） */
  serverSidePagination?: boolean;
  /** 是否有下一页（服务器端分页使用） */
  hasNext?: boolean;
  /** 是否有上一页（服务器端分页使用） */
  hasPrevious?: boolean;
  /** 是否启用行选择 */
  enableRowSelection?: boolean;
  /** 选中的记录 */
  selectedRecords?: T[];
  /** 选择状态变更回调 */
  onSelectedRecordsChange?: (records: T[]) => void;
  /** 记录ID获取函数，用于判断唯一性 */
  getRecordId?: (record: T) => string | number;
  /** 是否可以选择某条记录的函数 */
  isRecordSelectable?: (record: T) => boolean;
}

// 骨架加载组件
function SkeletonRow<T extends object>({
  columns,
  className,
  enableRowSelection,
}: {
  columns: ColumnDef<T>[];
  className?: string;
  enableRowSelection?: boolean;
}) {
  return (
    <TableRow className={className}>
      {enableRowSelection && (
        <TableCell className="w-12">
          <div className="h-4 w-4 animate-pulse rounded bg-muted" />
        </TableCell>
      )}
      {columns.map((column) => (
        <TableCell key={column.id}>
          <div className="h-4 w-full animate-pulse rounded bg-muted" />
        </TableCell>
      ))}
    </TableRow>
  );
}

// 表格头部组件
function DataTableHeader<T extends object>({
  columns,
  sorting,
  onSortingChange,
  enableRowSelection,
  selectedRecords = [],
  displayData,
  onSelectAll,
  isRecordSelectable,
}: {
  columns: ColumnDef<T>[];
  sorting?: SortingState[];
  onSortingChange?: (sorting: SortingState[]) => void;
  enableRowSelection?: boolean;
  selectedRecords?: T[];
  displayData: T[];
  onSelectAll?: (checked: boolean) => void;
  isRecordSelectable?: (record: T) => boolean;
}) {
  const checkboxRef = React.useRef<HTMLButtonElement>(null);

  const handleSort = (columnId: string) => {
    if (!onSortingChange) return;

    const existingSort = sorting?.find((s) => s.id === columnId);
    if (existingSort) {
      if (existingSort.desc) {
        // Remove sorting
        onSortingChange(sorting?.filter((s) => s.id !== columnId) || []);
      } else {
        // Change to descending
        onSortingChange(
          sorting?.map((s) => (s.id === columnId ? { ...s, desc: true } : s)) ||
            []
        );
      }
    } else {
      // Add ascending sort
      onSortingChange([{ id: columnId, desc: false }]);
    }
  };

  // 计算全选状态
  const selectableData = displayData.filter(
    (record) => !isRecordSelectable || isRecordSelectable(record)
  );
  const isAllSelected =
    selectableData.length > 0 &&
    selectableData.every((record) =>
      selectedRecords.some(
        (selected) => JSON.stringify(selected) === JSON.stringify(record)
      )
    );
  const isIndeterminate = selectedRecords.length > 0 && !isAllSelected;

  // 设置 indeterminate 状态
  React.useEffect(() => {
    if (checkboxRef.current) {
      // 对于checkbox，indeterminate是DOM属性而不是React属性
      const element = checkboxRef.current.querySelector(
        'input[type="checkbox"]'
      ) as HTMLInputElement;
      if (element) {
        element.indeterminate = isIndeterminate;
      }
    }
  }, [isIndeterminate]);

  return (
    <TableHeader>
      <TableRow>
        {enableRowSelection && (
          <TableHead className="w-12">
            <Checkbox
              ref={checkboxRef}
              checked={isAllSelected}
              onCheckedChange={(checked) => {
                onSelectAll?.(!!checked);
              }}
              aria-label="全选"
            />
          </TableHead>
        )}
        {columns.map((column) => {
          const sortState = sorting?.find((s) => s.id === column.id);
          const isSortable = column.sortable && onSortingChange;

          return (
            <TableHead
              key={column.id}
              className={cn(
                column.className,
                isSortable && 'cursor-pointer select-none hover:bg-muted/50'
              )}
              onClick={isSortable ? () => handleSort(column.id) : undefined}
            >
              <div className="flex items-center gap-2">
                {column.header}
                {isSortable && (
                  <span className="text-muted-foreground">
                    {sortState ? (sortState.desc ? '↓' : '↑') : '↕'}
                  </span>
                )}
              </div>
            </TableHead>
          );
        })}
      </TableRow>
    </TableHeader>
  );
}

// 分页控件组件
function DataTablePagination({
  pagination,
  onPaginationChange,
  totalItems,
  pageSizeOptions = [10, 20, 50, 100],
  hasNext,
  hasPrevious,
}: {
  pagination: PaginationState;
  onPaginationChange: (pagination: PaginationState) => void;
  totalItems: number;
  pageSizeOptions?: number[];
  hasNext?: boolean;
  hasPrevious?: boolean;
}) {
  const totalPages = Math.ceil(totalItems / pagination.pageSize);
  const currentPage = pagination.pageIndex + 1;
  const startItem =
    totalItems > 0 ? pagination.pageIndex * pagination.pageSize + 1 : 0;
  const endItem = Math.min(startItem + pagination.pageSize - 1, totalItems);

  // 如果提供了 hasNext 和 hasPrevious，则使用它们，否则回退到计算逻辑
  const canPreviousPage =
    hasPrevious !== undefined ? hasPrevious : pagination.pageIndex > 0;
  const canNextPage =
    hasNext !== undefined ? hasNext : pagination.pageIndex < totalPages - 1;

  const handlePreviousPage = () => {
    if (canPreviousPage) {
      onPaginationChange({
        ...pagination,
        pageIndex: pagination.pageIndex - 1,
      });
    }
  };

  const handleNextPage = () => {
    if (canNextPage) {
      onPaginationChange({
        ...pagination,
        pageIndex: pagination.pageIndex + 1,
      });
    }
  };

  const handlePageSizeChange = (newPageSize: number) => {
    onPaginationChange({
      pageIndex: 0,
      pageSize: newPageSize,
    });
  };

  return (
    <div className="flex items-center justify-between px-2 py-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>每页显示</span>
        <select
          value={pagination.pageSize}
          onChange={(e) => handlePageSizeChange(Number(e.target.value))}
          className="h-8 w-16 rounded border border-input bg-background px-2 text-sm"
        >
          {pageSizeOptions.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
        <span>条</span>
      </div>

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>
          {totalItems > 0
            ? `第 ${startItem}-${endItem} 条，共 ${totalItems} 条`
            : `共 0 条`}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">
          第 {currentPage} / {totalPages} 页
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePreviousPage}
            disabled={!canPreviousPage}
          >
            上一页
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNextPage}
            disabled={!canNextPage}
          >
            下一页
          </Button>
        </div>
      </div>
    </div>
  );
}

// 主要的 DataTable 组件
export function DataTable<T extends object>({
  data,
  columns,
  loading = false,
  skeletonRows = 5,
  pagination: controlledPagination,
  onPaginationChange,
  sorting,
  onSortingChange,
  onRowClick,
  className,
  enablePagination = true,
  pageSizeOptions,
  emptyContent,
  totalItems,
  serverSidePagination = false,
  enableRowSelection = false,
  selectedRecords = [],
  onSelectedRecordsChange,
  getRecordId,
  isRecordSelectable,
  hasNext,
  hasPrevious,
}: DataTableProps<T>) {
  // 内部分页状态（当未提供外部控制时）
  const internalPagination = usePagination(0, 10);

  // 使用受控或非受控分页
  const paginationState = controlledPagination || internalPagination.pagination;
  const setPaginationState =
    onPaginationChange || internalPagination.setPagination;

  // 计算显示的数据（移动到前面，避免在使用前声明的问题）
  const displayData = React.useMemo(() => {
    // 如果不启用分页或使用服务器端分页，直接返回数据
    if (!enablePagination || serverSidePagination) return data;

    // 客户端分页
    const start = paginationState.pageIndex * paginationState.pageSize;
    const end = start + paginationState.pageSize;
    return data.slice(start, end);
  }, [data, paginationState, enablePagination, serverSidePagination]);

  // 默认的记录ID获取函数
  const defaultGetRecordId = React.useCallback((record: T) => {
    // 尝试使用常见的ID字段
    if ('id' in record) return String((record as Record<string, unknown>).id);
    if ('_id' in record) return String((record as Record<string, unknown>)._id);
    if ('key' in record) return String((record as Record<string, unknown>).key);
    // 回退到JSON序列化（不推荐，仅作为最后手段）
    return JSON.stringify(record);
  }, []);

  const recordIdGetter = getRecordId || defaultGetRecordId;

  // 检查记录是否被选中
  const isRecordSelected = React.useCallback(
    (record: T) => {
      const recordId = recordIdGetter(record);
      return selectedRecords.some(
        (selected) => recordIdGetter(selected) === recordId
      );
    },
    [selectedRecords, recordIdGetter]
  );

  // 切换单个记录的选择状态
  const toggleRecordSelection = React.useCallback(
    (record: T) => {
      if (!onSelectedRecordsChange) return;

      const recordId = recordIdGetter(record);
      const isSelected = isRecordSelected(record);

      if (isSelected) {
        // 取消选择
        onSelectedRecordsChange(
          selectedRecords.filter(
            (selected) => recordIdGetter(selected) !== recordId
          )
        );
      } else {
        // 添加选择
        onSelectedRecordsChange([...selectedRecords, record]);
      }
    },
    [selectedRecords, onSelectedRecordsChange, recordIdGetter, isRecordSelected]
  );

  // 全选/取消全选
  const handleSelectAll = React.useCallback(
    (checked: boolean) => {
      if (!onSelectedRecordsChange) return;

      if (checked) {
        // 选择当前页面所有可选择的记录
        const selectableRecords = displayData.filter(
          (record) => !isRecordSelectable || isRecordSelectable(record)
        );

        // 合并已选择的记录（去重）
        const newSelectedRecords = [...selectedRecords];
        selectableRecords.forEach((record) => {
          if (!isRecordSelected(record)) {
            newSelectedRecords.push(record);
          }
        });

        onSelectedRecordsChange(newSelectedRecords);
      } else {
        // 取消选择当前页面的所有记录
        const currentPageIds = displayData.map((record) =>
          recordIdGetter(record)
        );
        onSelectedRecordsChange(
          selectedRecords.filter(
            (selected) => !currentPageIds.includes(recordIdGetter(selected))
          )
        );
      }
    },
    [
      displayData,
      selectedRecords,
      onSelectedRecordsChange,
      isRecordSelectable,
      isRecordSelected,
      recordIdGetter,
    ]
  );

  // 渲染单元格内容
  const renderCell = React.useCallback((item: T, column: ColumnDef<T>) => {
    if (column.cell) {
      return column.cell(item);
    }
    if (column.accessorKey) {
      const value = item[column.accessorKey];
      return value?.toString() || '';
    }
    return '';
  }, []);

  // 空状态内容
  const defaultEmptyContent = (
    <div className="flex h-24 items-center justify-center text-muted-foreground">
      暂无数据
    </div>
  );

  return (
    <div className={cn('space-y-4', className)}>
      <div className="rounded-md border">
        <Table>
          <DataTableHeader
            columns={columns}
            sorting={sorting}
            onSortingChange={onSortingChange}
            enableRowSelection={enableRowSelection}
            selectedRecords={selectedRecords}
            displayData={displayData}
            onSelectAll={handleSelectAll}
            isRecordSelectable={isRecordSelectable}
          />
          <TableBody>
            {loading ? (
              // 加载状态显示骨架
              Array.from({ length: skeletonRows }).map((_, index) => (
                <SkeletonRow
                  key={index}
                  columns={columns}
                  enableRowSelection={enableRowSelection}
                />
              ))
            ) : displayData.length > 0 ? (
              // 正常数据显示
              displayData.map((item, index) => {
                const isSelected = enableRowSelection && isRecordSelected(item);
                const isSelectable =
                  !isRecordSelectable || isRecordSelectable(item);

                return (
                  <TableRow
                    key={index}
                    className={cn(
                      onRowClick && 'cursor-pointer hover:bg-muted/50',
                      isSelected && 'bg-muted/50'
                    )}
                    onClick={onRowClick ? () => onRowClick(item) : undefined}
                  >
                    {enableRowSelection && (
                      <TableCell className="w-12">
                        <Checkbox
                          checked={isSelected}
                          disabled={!isSelectable}
                          onCheckedChange={() => {
                            if (isSelectable) {
                              toggleRecordSelection(item);
                            }
                          }}
                          onClick={(e) => e.stopPropagation()}
                          aria-label={`选择${renderCell(item, columns[0])}`}
                        />
                      </TableCell>
                    )}
                    {columns.map((column) => (
                      <TableCell key={column.id} className={column.className}>
                        {renderCell(item, column)}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            ) : (
              // 空状态
              <TableRow>
                <TableCell
                  colSpan={columns.length + (enableRowSelection ? 1 : 0)}
                  className="h-24 text-center"
                >
                  {emptyContent || defaultEmptyContent}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页控件 */}
      {enablePagination && !loading && (
        <DataTablePagination
          pagination={paginationState}
          onPaginationChange={setPaginationState}
          totalItems={serverSidePagination ? totalItems || 0 : data.length}
          pageSizeOptions={pageSizeOptions}
          hasNext={serverSidePagination ? hasNext : undefined}
          hasPrevious={serverSidePagination ? hasPrevious : undefined}
        />
      )}
    </div>
  );
}

// 导出类型供外部使用
export type { PaginationState };
