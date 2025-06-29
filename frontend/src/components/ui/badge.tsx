/* eslint-disable react-refresh/only-export-components */
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        outline: 'text-foreground',
        // 媒体文件状态相关的颜色 - 使用设计tokens
        completed:
          'border-transparent bg-primary-100 text-primary-800 hover:bg-primary-100/80',
        progress:
          'border-transparent bg-success-100 text-success-800 hover:bg-success-100/80',
        pending:
          'border-transparent bg-warning-100 text-warning-800 hover:bg-warning-100/80',
        returned:
          'border-transparent bg-secondary-100 text-secondary-800 hover:bg-secondary-100/80',
        canceled:
          'border-transparent bg-danger-100 text-danger-800 hover:bg-danger-100/80',
        // 保留原有变体以保持兼容性
        processing:
          'border-transparent bg-blue-100 text-blue-800 hover:bg-blue-100/80',
        failed:
          'border-transparent bg-red-100 text-red-800 hover:bg-red-100/80',
        conflict:
          'border-transparent bg-orange-100 text-orange-800 hover:bg-orange-100/80',
        'no-match':
          'border-transparent bg-purple-100 text-purple-800 hover:bg-purple-100/80',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };

export type BadgeVariant = VariantProps<typeof badgeVariants>['variant'];
