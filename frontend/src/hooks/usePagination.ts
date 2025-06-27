import { useState, useCallback } from 'react';

export interface PaginationState {
  pageIndex: number;
  pageSize: number;
}

export interface UsePaginationReturn {
  pagination: PaginationState;
  setPagination: (
    updater: PaginationState | ((prev: PaginationState) => PaginationState)
  ) => void;
  nextPage: () => void;
  previousPage: () => void;
  setPageSize: (pageSize: number) => void;
  setPageIndex: (pageIndex: number) => void;
  canNextPage: (totalItems: number) => boolean;
  canPreviousPage: boolean;
  pageCount: (totalItems: number) => number;
  getPageItems: <T>(items: T[]) => T[];
}

export function usePagination(
  initialPageIndex = 0,
  initialPageSize = 10
): UsePaginationReturn {
  const [pagination, setPaginationState] = useState<PaginationState>({
    pageIndex: initialPageIndex,
    pageSize: initialPageSize,
  });

  const setPagination = useCallback(
    (
      updater: PaginationState | ((prev: PaginationState) => PaginationState)
    ) => {
      setPaginationState((prevState) => {
        const newState =
          typeof updater === 'function' ? updater(prevState) : updater;
        return {
          pageIndex: Math.max(0, newState.pageIndex),
          pageSize: Math.max(1, newState.pageSize),
        };
      });
    },
    []
  );

  const nextPage = useCallback(() => {
    setPaginationState((prev) => ({
      ...prev,
      pageIndex: prev.pageIndex + 1,
    }));
  }, []);

  const previousPage = useCallback(() => {
    setPaginationState((prev) => ({
      ...prev,
      pageIndex: Math.max(0, prev.pageIndex - 1),
    }));
  }, []);

  const setPageSize = useCallback((pageSize: number) => {
    setPaginationState((prev) => ({
      ...prev,
      pageSize: Math.max(1, pageSize),
      pageIndex: 0, // Reset to first page when changing page size
    }));
  }, []);

  const setPageIndex = useCallback((pageIndex: number) => {
    setPaginationState((prev) => ({
      ...prev,
      pageIndex: Math.max(0, pageIndex),
    }));
  }, []);

  const canNextPage = useCallback(
    (totalItems: number) => {
      const totalPages = Math.ceil(totalItems / pagination.pageSize);
      return pagination.pageIndex < totalPages - 1;
    },
    [pagination.pageIndex, pagination.pageSize]
  );

  const canPreviousPage = pagination.pageIndex > 0;

  const pageCount = useCallback(
    (totalItems: number) => Math.ceil(totalItems / pagination.pageSize),
    [pagination.pageSize]
  );

  const getPageItems = useCallback(
    <T>(items: T[]): T[] => {
      const start = pagination.pageIndex * pagination.pageSize;
      const end = start + pagination.pageSize;
      return items.slice(start, end);
    },
    [pagination.pageIndex, pagination.pageSize]
  );

  return {
    pagination,
    setPagination,
    nextPage,
    previousPage,
    setPageSize,
    setPageIndex,
    canNextPage,
    canPreviousPage,
    pageCount,
    getPageItems,
  };
}
