import { useEffect, useState, useCallback } from 'react';
import { useConfig } from '@/hooks/useConfig';
import { ConfigItem } from '@/components/ConfigItem';
import { Button } from '@/components/ui/button';
import { Toast } from '@/lib/toast';

export function Settings() {
  const { config, blacklistKeys, loading, error, fetchConfig, saveConfig } =
    useConfig();

  // 本地编辑状态 - 维护配置的草稿版本
  const [draftConfig, setDraftConfig] = useState<Record<string, unknown>>({});
  const [isSaving, setIsSaving] = useState(false);

  // 页面加载时获取配置
  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  // 当配置加载完成时，初始化草稿状态
  useEffect(() => {
    if (config) {
      setDraftConfig({ ...config });
    }
  }, [config]);

  // 处理单个配置项的变化
  const handleConfigChange = useCallback((key: string, value: unknown) => {
    setDraftConfig((prev) => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  // 计算变化的配置项
  const getChangedConfig = useCallback(() => {
    if (!config) return {};

    const changes: Record<string, unknown> = {};
    Object.keys(draftConfig).forEach((key) => {
      if (draftConfig[key] !== config[key]) {
        changes[key] = draftConfig[key];
      }
    });
    return changes;
  }, [config, draftConfig]);

  // 保存配置
  const handleSave = useCallback(async () => {
    const changes = getChangedConfig();

    if (Object.keys(changes).length === 0) {
      Toast.info('没有检测到配置变化');
      return;
    }

    setIsSaving(true);
    try {
      await saveConfig(changes);
      Toast.success(`已成功更新 ${Object.keys(changes).length} 项配置`);
    } catch (err) {
      Toast.error(err instanceof Error ? err.message : '保存配置失败');
    } finally {
      setIsSaving(false);
    }
  }, [getChangedConfig, saveConfig]);

  // 重置配置到原始状态
  const handleReset = useCallback(() => {
    if (config) {
      setDraftConfig({ ...config });
      Toast.info('已重置所有修改');
    }
  }, [config]);

  // 检查是否有未保存的变化
  const hasChanges = Object.keys(getChangedConfig()).length > 0;

  if (loading && !config) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-foreground mb-4">系统设置</h1>
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">加载配置中...</div>
        </div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-foreground mb-4">系统设置</h1>
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <div className="text-destructive">加载配置失败: {error}</div>
          <Button onClick={fetchConfig} variant="outline">
            重试
          </Button>
        </div>
      </div>
    );
  }

  if (!config) {
    return null;
  }

  // 按类别分组配置项
  const configGroups = {
    'OpenAI/LLM': Object.keys(config).filter(
      (key) => key.startsWith('OPENAI_') || key.includes('LLM')
    ),
    TMDB: Object.keys(config).filter((key) => key.startsWith('TMDB_')),
    扫描与文件: Object.keys(config).filter(
      (key) =>
        key.includes('SCAN_') ||
        key.includes('FILE') ||
        key.includes('DIR') ||
        key.includes('VIDEO_')
    ),
    系统运行: Object.keys(config).filter(
      (key) =>
        key.includes('LOG_') ||
        key.includes('APP_') ||
        key.includes('WORKER_') ||
        key.includes('PRODUCER_') ||
        key.includes('CORS_')
    ),
    功能开关: Object.keys(config).filter((key) => key.startsWith('ENABLE_')),
    其他: Object.keys(config).filter((key) => {
      const groups = [
        'OPENAI_',
        'LLM',
        'TMDB_',
        'SCAN_',
        'FILE',
        'DIR',
        'VIDEO_',
        'LOG_',
        'APP_',
        'WORKER_',
        'PRODUCER_',
        'CORS_',
        'ENABLE_',
      ];
      return !groups.some((prefix) => key.includes(prefix));
    }),
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">系统设置</h1>
          <p className="text-muted-foreground">
            配置系统参数，不在黑名单内的配置项可以修改
          </p>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2">
          <Button
            onClick={handleReset}
            variant="outline"
            disabled={!hasChanges || isSaving}
          >
            重置
          </Button>
          <Button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className="min-w-20"
          >
            {isSaving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>

      {/* 变化提示 */}
      {hasChanges && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="text-amber-800 text-sm">
            检测到 {Object.keys(getChangedConfig()).length}{' '}
            项配置变化，记得点击"保存"按钮保存修改
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-red-800 text-sm">{error}</div>
        </div>
      )}

      {/* 配置项分组显示 */}
      <div className="space-y-6">
        {Object.entries(configGroups).map(([groupName, keys]) => {
          if (keys.length === 0) return null;

          return (
            <div key={groupName} className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-secondary-900 mb-4">
                {groupName}
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                {keys.map((key) => (
                  <ConfigItem
                    key={key}
                    keyName={key}
                    value={draftConfig[key]}
                    editable={!blacklistKeys.includes(key)}
                    onChange={(value) => handleConfigChange(key, value)}
                    description={getConfigDescription(key)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* 底部提示 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-secondary-900 mb-3">
          使用说明
        </h3>
        <div className="text-sm text-secondary-600 space-y-1">
          <p>• 只有不在黑名单内的配置项可以修改，其他配置项为只读</p>
          <p>• 配置修改后需要点击"保存"按钮才会生效</p>
          <p>• 某些配置项的修改可能需要重启应用才能完全生效</p>
          <p>• 当前黑名单配置项：{blacklistKeys.join(', ')}</p>
        </div>
      </div>
    </div>
  );
}

// 获取配置项的描述信息
function getConfigDescription(key: string): string {
  const descriptions: Record<string, string> = {
    OPENAI_API_KEY: 'OpenAI API 密钥',
    OPENAI_API_BASE: 'OpenAI API 基础URL，可配置代理',
    OPENAI_MODEL: 'OpenAI 模型名称',
    TMDB_API_KEY: 'TMDB API 密钥',
    TMDB_LANGUAGE: 'TMDB API 返回语言',
    TMDB_CONCURRENCY: 'TMDB API 并发限制',
    SOURCE_DIR: '待扫描的源文件夹路径',
    TARGET_DIR: '整理后的目标文件夹路径',
    SCAN_INTERVAL_SECONDS: '扫描器两次扫描之间的等待时间（秒）',
    SCAN_EXCLUDE_TARGET_DIR: '扫描时是否自动排除目标目录',
    SCAN_FOLLOW_SYMLINKS: '扫描时是否跟随符号链接',
    MIN_FILE_SIZE_MB: '扫描时忽略小于此大小的文件（MB）',
    VIDEO_EXTENSIONS: '允许处理的媒体文件扩展名',
    LOG_LEVEL: '日志级别',
    APP_ENV: '运行环境',
    ENABLE_TMDB: '是否启用 TMDB API 调用',
    ENABLE_LLM: '是否启用 LLM 分析功能',
    WORKER_COUNT: '处理媒体文件的工作者协程数量',
    PRODUCER_BATCH_SIZE: 'Producer 每次处理的文件数量',
    PRODUCER_INTERVAL_SECONDS: 'Producer 轮询间隔时间（秒）',
    CORS_ORIGINS: '允许跨域访问的源地址',
  };

  return descriptions[key] || '';
}

export default Settings;
