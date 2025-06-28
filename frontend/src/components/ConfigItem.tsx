import * as React from 'react';
import { Input } from '@/components/ui/input';
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
 * 根据 editable 属性决定渲染可编辑的 Input 或只读的文本
 * 支持不同类型的值（字符串、数字、布尔值）的正确转换
 */
export const ConfigItem = React.forwardRef<HTMLDivElement, ConfigItemProps>(
  ({ keyName, value, editable, onChange, description, className }, ref) => {
    // 处理不同类型的值显示
    const getDisplayValue = (val: unknown): string => {
      if (val === null || val === undefined) return '';
      if (typeof val === 'boolean') return val.toString();
      if (typeof val === 'number') return val.toString();
      if (typeof val === 'string') return val;
      return JSON.stringify(val);
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

    const displayValue = getDisplayValue(value);

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
            <Input
              id={`config-${keyName}`}
              value={displayValue}
              onChange={(e) => handleInputChange(e.target.value)}
              placeholder={`输入 ${keyName} 的值`}
              className="w-full"
            />
          ) : (
            <div
              className={cn(
                'flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm',
                'text-muted-foreground cursor-not-allowed'
              )}
            >
              {displayValue || '(空值)'}
            </div>
          )}
        </div>

        {/* 类型提示 */}
        <div className="text-xs text-muted-foreground">
          类型: {typeof value} {!editable && '(只读)'}
        </div>
      </div>
    );
  }
);

ConfigItem.displayName = 'ConfigItem';
