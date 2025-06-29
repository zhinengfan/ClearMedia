import * as React from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

export interface ConfigItemProps {
  /** 配置项的键名 */
  keyName: string;
  /** 配置项的值 */
  value: unknown;
  /** 是否可编辑 */
  editable: boolean;
  /** 值变化时的回调函数 */
  onChange: (value: unknown) => void;
  /** 配置项的描述（可选） */
  description?: string;
  /** 自定义类名 */
  className?: string;
}

/**
 * ConfigItem 组件 - 用于渲染单个配置项
 *
 * 根据 editable 属性决定渲染可编辑的 Input/Select 或只读的文本
 * 支持不同类型的值（字符串、数字、布尔值）的正确转换
 */
export const ConfigItem = React.forwardRef<HTMLDivElement, ConfigItemProps>(
  ({ keyName, value, editable, onChange, description, className }, ref) => {
    // 定义敏感字段
    const sensitiveFields = React.useMemo(
      () => new Set(['OPENAI_API_KEY', 'TMDB_API_KEY', 'DATABASE_URL']),
      []
    );

    // 定义特殊字段的选项
    const fieldOptions = React.useMemo(() => {
      const options: Record<string, Array<{ value: string; label: string }>> = {
        LOG_LEVEL: [
          { value: 'DEBUG', label: 'DEBUG' },
          { value: 'INFO', label: 'INFO' },
          { value: 'WARNING', label: 'WARNING' },
          { value: 'ERROR', label: 'ERROR' },
          { value: 'CRITICAL', label: 'CRITICAL' },
        ],
      };
      return options;
    }, []);

    // 定义配置项的默认值
    const defaultValues = React.useMemo(() => {
      const defaults: Record<string, unknown> = {
        // OpenAI/LLM 配置
        OPENAI_API_KEY: '',
        OPENAI_API_BASE: 'https://api.openai.com/v1',
        OPENAI_MODEL: 'gpt-3.5-turbo',
        ENABLE_LLM: true,

        // TMDB 配置
        TMDB_API_KEY: '',
        TMDB_LANGUAGE: 'zh-CN',
        TMDB_CONCURRENCY: 3,
        ENABLE_TMDB: true,

        // 扫描与文件配置
        SOURCE_DIR: '/path/to/source',
        TARGET_DIR: '/path/to/target',
        SCAN_INTERVAL_SECONDS: 300,
        SCAN_EXCLUDE_TARGET_DIR: true,
        SCAN_FOLLOW_SYMLINKS: false,
        MIN_FILE_SIZE_MB: 50,
        VIDEO_EXTENSIONS: '.mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v',

        // 系统运行配置
        LOG_LEVEL: 'INFO',
        APP_ENV: 'production',
        WORKER_COUNT: 4,
        PRODUCER_BATCH_SIZE: 10,
        PRODUCER_INTERVAL_SECONDS: 30,
        CORS_ORIGINS: '*',
      };
      return defaults;
    }, []);

    // 判断是否为敏感字段
    const isSensitive = sensitiveFields.has(keyName);

    // 判断是否有特殊选项
    const hasCustomOptions = fieldOptions[keyName];

    // 获取默认值
    const defaultValue = defaultValues[keyName];

    // 敏感字段的显示状态（true: 显示真实值, false: 显示****）
    const [showRealValue, setShowRealValue] = React.useState(false);

    // 处理不同类型的值显示
    const getDisplayValue = (val: unknown, hideValue = false): string => {
      if (val === null || val === undefined) return '';

      let displayVal = '';
      if (typeof val === 'boolean') displayVal = val.toString();
      else if (typeof val === 'number') displayVal = val.toString();
      else if (typeof val === 'string') displayVal = val;
      else displayVal = JSON.stringify(val);

      // 如果是敏感字段且需要隐藏，返回 ****
      if (hideValue && isSensitive && displayVal) {
        return '****'.repeat(Math.max(1, Math.floor(displayVal.length / 4)));
      }

      return displayVal;
    };

    // 格式化默认值显示
    const formatDefaultValue = (val: unknown): string => {
      if (val === null || val === undefined) return '无';
      if (typeof val === 'string') return `"${val}"`;
      return String(val);
    };

    // 处理输入值的类型转换
    const handleInputChange = (inputValue: string) => {
      const originalValue = value;

      // 根据原始值的类型进行转换
      if (typeof originalValue === 'boolean') {
        // 布尔值：true/false 字符串转换
        const lowerValue = inputValue.toLowerCase().trim();
        if (lowerValue === 'true') {
          onChange(true);
        } else if (lowerValue === 'false') {
          onChange(false);
        } else {
          // 非标准布尔值，保持字符串
          onChange(inputValue);
        }
      } else if (typeof originalValue === 'number') {
        // 数字类型：尝试解析为数字
        const numValue = Number(inputValue);
        if (!isNaN(numValue)) {
          onChange(numValue);
        } else {
          // 解析失败，保持字符串
          onChange(inputValue);
        }
      } else {
        // 其他类型保持字符串
        onChange(inputValue);
      }
    };

    // 处理 boolean 类型的 Select 变化
    const handleBooleanSelectChange = (selectedValue: string) => {
      onChange(selectedValue === 'true');
    };

    // 处理自定义选项的 Select 变化
    const handleCustomSelectChange = (selectedValue: string) => {
      onChange(selectedValue);
    };

    // 根据当前显示状态获取显示值
    const displayValue = getDisplayValue(value, isSensitive && !showRealValue);
    // 获取真实值（用于编辑）
    const realValue = getDisplayValue(value, false);

    // 渲染编辑控件
    const renderEditableControl = () => {
      // 如果有自定义选项，使用自定义下拉选择器
      if (hasCustomOptions) {
        const options = fieldOptions[keyName];
        const currentValue = value as string;

        return (
          <Select
            value={currentValue || ''}
            onValueChange={handleCustomSelectChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={`选择 ${keyName}`} />
            </SelectTrigger>
            <SelectContent>
              {options.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      }

      if (typeof value === 'boolean') {
        // 布尔类型使用 Select 下拉选择器
        return (
          <Select
            value={value.toString()}
            onValueChange={handleBooleanSelectChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="选择布尔值" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="true">true</SelectItem>
              <SelectItem value="false">false</SelectItem>
            </SelectContent>
          </Select>
        );
      } else if (typeof value === 'number') {
        // 数字类型使用 number input
        return (
          <Input
            id={`config-${keyName}`}
            type="number"
            value={realValue}
            onChange={(e) => handleInputChange(e.target.value)}
            placeholder={`输入 ${keyName} 的值`}
            className="w-full"
          />
        );
      } else {
        // 其他类型使用文本输入框
        return (
          <div className="relative">
            <Input
              id={`config-${keyName}`}
              type={isSensitive && !showRealValue ? 'password' : 'text'}
              value={realValue}
              onChange={(e) => handleInputChange(e.target.value)}
              placeholder={`输入 ${keyName} 的值`}
              className={cn('w-full', isSensitive && 'pr-10')}
            />
            {isSensitive && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowRealValue(!showRealValue)}
              >
                {showRealValue ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            )}
          </div>
        );
      }
    };

    return (
      <div
        ref={ref}
        className={cn(
          'flex flex-col gap-2 p-4 border border-border rounded-lg bg-card',
          className
        )}
      >
        {/* 配置项标签 */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor={`config-${keyName}`}
            className="text-sm font-medium text-foreground"
          >
            {keyName}
          </label>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
        </div>

        {/* 配置项控件 */}
        <div className="flex-1">
          {editable ? (
            renderEditableControl()
          ) : (
            <div className="relative">
              <div
                className={cn(
                  'flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm',
                  'text-muted-foreground cursor-not-allowed',
                  isSensitive && 'pr-10'
                )}
              >
                {displayValue || '(空值)'}
              </div>
              {isSensitive && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowRealValue(!showRealValue)}
                >
                  {showRealValue ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
              )}
            </div>
          )}
        </div>

        {/* 类型提示和默认值 */}
        <div className="text-xs text-muted-foreground">
          类型: {typeof value}
          {defaultValue !== undefined && (
            <span>, 默认值: {formatDefaultValue(defaultValue)}</span>
          )}
          {!editable && ' (只读)'}
          {isSensitive && ' (敏感信息)'}
          {hasCustomOptions && ' (预设选项)'}
        </div>
      </div>
    );
  }
);

ConfigItem.displayName = 'ConfigItem';
