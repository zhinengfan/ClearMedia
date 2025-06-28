import type { paths } from '@/types/openapi';

// 自定义错误类
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = 'ApiError';
  }
}

// 类型别名，基于生成的paths
export type StatsResponse =
  paths['/api/stats']['get']['responses'][200]['content']['application/json'];
export type MediaFileItem =
  paths['/api/files']['get']['responses'][200]['content']['application/json']['items'][number];
export type FilesResponse =
  paths['/api/files']['get']['responses'][200]['content']['application/json'];
export type FileDetail =
  paths['/api/files/{file_id}']['get']['responses'][200]['content']['application/json'];
export type RetryResponse =
  paths['/api/files/{file_id}/retry']['post']['responses'][200]['content']['application/json'];
export type FileSuggestResponse =
  paths['/api/files/suggest']['get']['responses'][200]['content']['application/json'];
export type ConfigResponse =
  paths['/api/config']['get']['responses'][200]['content']['application/json'];
export type ConfigUpdateResponse =
  paths['/api/config']['post']['responses'][200]['content']['application/json'];

// 查询参数类型
export type GetFilesParams = paths['/api/files']['get']['parameters']['query'];
export type GetFileSuggestParams =
  paths['/api/files/suggest']['get']['parameters']['query'];

// 基础API配置
const API_BASE_URL = 'http://localhost:8000';

// 泛型请求函数
export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);

    // 检查响应状态
    if (!response.ok) {
      let errorData: unknown;
      try {
        errorData = await response.json();
      } catch {
        errorData = null;
      }
      throw new ApiError(response.status, response.statusText, errorData);
    }

    // 解析JSON响应
    const data = await response.json();
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // 网络错误或其他错误
    throw new Error(
      `Request failed: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

// 业务API函数

/**
 * 获取统计数据
 */
export async function getStats(): Promise<StatsResponse> {
  return request<StatsResponse>('/api/stats');
}

/**
 * 获取文件列表
 */
export async function getFiles(
  params?: GetFilesParams
): Promise<FilesResponse> {
  const searchParams = new URLSearchParams();

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, value.toString());
      }
    });
  }

  const endpoint = searchParams.toString()
    ? `/api/files?${searchParams}`
    : '/api/files';
  return request<FilesResponse>(endpoint);
}

/**
 * 获取单个文件详情
 */
export async function getFileDetail(fileId: number): Promise<FileDetail> {
  return request<FileDetail>(`/api/files/${fileId}`);
}

/**
 * 重试处理文件
 */
export async function retryFile(fileId: number): Promise<RetryResponse> {
  return request<RetryResponse>(`/api/files/${fileId}/retry`, {
    method: 'POST',
  });
}

/**
 * 获取文件名建议
 */
export async function getFileSuggestions(
  params: GetFileSuggestParams
): Promise<FileSuggestResponse> {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, value.toString());
    }
  });

  return request<FileSuggestResponse>(`/api/files/suggest?${searchParams}`);
}

/**
 * 获取配置信息
 */
export async function getConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>('/api/config');
}

/**
 * 更新配置
 */
export async function updateConfig(
  configUpdates: Record<string, unknown>
): Promise<ConfigUpdateResponse> {
  return request<ConfigUpdateResponse>('/api/config', {
    method: 'POST',
    body: JSON.stringify(configUpdates),
  });
}

/**
 * 批量重试文件
 */
export async function batchRetryFiles(fileIds: number[]): Promise<{
  message: string;
  results: Array<{
    file_id: number;
    success: boolean;
    error?: string;
  }>;
}> {
  return request<{
    message: string;
    results: Array<{
      file_id: number;
      success: boolean;
      error?: string;
    }>;
  }>('/api/files/batch-retry', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ file_ids: fileIds }),
  });
}

/**
 * 批量删除文件（可选功能）
 */
export async function batchDeleteFiles(fileIds: number[]): Promise<{
  message: string;
  results: Array<{
    file_id: number;
    success: boolean;
    error?: string;
  }>;
}> {
  return request<{
    message: string;
    results: Array<{
      file_id: number;
      success: boolean;
      error?: string;
    }>;
  }>('/api/files/batch-delete', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ file_ids: fileIds }),
  });
}
