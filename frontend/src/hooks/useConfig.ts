import { useState, useCallback } from 'react';
import { getConfig, updateConfig, ApiError } from '@/lib/api';
import type { ConfigResponse, ConfigUpdateResponse } from '@/lib/api';

export interface UseConfigReturn {
  config: Record<string, unknown> | null;
  blacklistKeys: string[];
  loading: boolean;
  error: string | null;
  fetchConfig: () => Promise<void>;
  saveConfig: (partialUpdates: Record<string, unknown>) => Promise<void>;
}

/**
 * useConfig Hook - 封装配置获取与更新逻辑
 *
 * 提供配置数据管理功能，包括获取、更新配置以及状态管理
 *
 * @returns {UseConfigReturn} Hook 返回值对象
 */
export function useConfig(): UseConfigReturn {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [blacklistKeys, setBlacklistKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * 获取配置信息
   */
  const fetchConfig = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response: ConfigResponse = await getConfig();
      setConfig(response.config);
      setBlacklistKeys(response.blacklist_keys);
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? `获取配置失败: ${err.message}`
          : err instanceof Error
            ? `获取配置失败: ${err.message}`
            : '获取配置时发生未知错误';

      setError(errorMessage);
      console.error('Failed to fetch config:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 保存配置更新
   *
   * @param partialUpdates 要更新的配置项
   */
  const saveConfig = useCallback(
    async (partialUpdates: Record<string, unknown>) => {
      if (!partialUpdates || Object.keys(partialUpdates).length === 0) {
        setError('配置更新数据不能为空');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response: ConfigUpdateResponse =
          await updateConfig(partialUpdates);

        // 更新成功后同步本地状态
        setConfig(response.config);
        setBlacklistKeys(response.blacklist_keys);

        // 如果有被拒绝的配置项，记录警告但不视为错误
        if (response.rejected_keys && response.rejected_keys.length > 0) {
          console.warn('以下配置项被拒绝更新:', response.rejected_keys);
        }
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? `保存配置失败: ${err.message}`
            : err instanceof Error
              ? `保存配置失败: ${err.message}`
              : '保存配置时发生未知错误';

        setError(errorMessage);
        console.error('Failed to save config:', err);
        throw err; // 重新抛出错误，让调用者可以处理
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    config,
    blacklistKeys,
    loading,
    error,
    fetchConfig,
    saveConfig,
  };
}
