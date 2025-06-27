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
        // 媒体文件状态相关的颜色
        completed:
          'border-transparent bg-green-100 text-green-800 hover:bg-green-100/80',
        processing:
          'border-transparent bg-blue-100 text-blue-800 hover:bg-blue-100/80',
        pending:
          'border-transparent bg-yellow-100 text-yellow-800 hover:bg-yellow-100/80',
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
