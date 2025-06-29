import * as React from 'react';
import { createPortal } from 'react-dom';
import { cva, type VariantProps } from 'class-variance-authority';
import { X } from 'lucide-react';

import { cn } from '@/lib/utils';

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

const sheetContentVariants = cva(
  'fixed right-0 top-0 h-full bg-white border-l border-gray-200 shadow-lg z-50 transition-transform duration-300 ease-in-out overflow-auto data-[state=closed]:translate-x-full data-[state=open]:translate-x-0',
  {
    variants: {
      size: {
        sm: 'w-80 max-sm:w-full max-sm:border-l-0',
        md: 'w-96 max-sm:w-full max-sm:border-l-0',
        lg: 'w-[480px] max-sm:w-full max-sm:border-l-0',
        xl: 'w-[600px] max-sm:w-full max-sm:border-l-0',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
);

interface SheetContentProps
  extends React.ComponentProps<'div'>,
    VariantProps<typeof sheetContentVariants> {
  showCloseButton?: boolean;
  onClose?: () => void;
  state?: 'open' | 'closed';
}

function Sheet({ open, onOpenChange, children }: SheetProps) {
  const [mounted, setMounted] = React.useState(false);
  const [isVisible, setIsVisible] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  React.useEffect(() => {
    if (open) {
      setIsVisible(true);
      // 下一帧触发 translate-x 过渡
      const timer = setTimeout(() => {
        /* no-op: 仅用于等待下一帧 */
      }, 10);
      return () => clearTimeout(timer);
    } else {
      // 延迟卸载，给动画时间
      const timer = setTimeout(() => {
        setIsVisible(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [open]);

  React.useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && open) {
        onOpenChange(false);
      }
    };

    if (open) {
      document.addEventListener('keydown', handleEscape);
      // 防止背景滚动
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [open, onOpenChange]);

  if (!mounted || !isVisible) return null;

  return createPortal(children, document.body);
}

interface SheetOverlayProps extends React.ComponentProps<'div'> {
  state?: 'open' | 'closed';
}

function SheetOverlay({
  className,
  onClick,
  state = 'open',
  ...props
}: SheetOverlayProps) {
  return (
    <div
      data-slot="sheet-overlay"
      data-state={state}
      className={cn(
        'fixed inset-0 z-40 transition-opacity duration-300 ease-in-out',
        'data-[state=open]:bg-black/50 data-[state=closed]:bg-black/0',
        className
      )}
      onClick={onClick}
      {...props}
    />
  );
}

function SheetContent({
  className,
  size,
  showCloseButton = true,
  onClose,
  state = 'open',
  children,
  ...props
}: SheetContentProps) {
  return (
    <div
      data-slot="sheet-content"
      data-state={state}
      className={cn(sheetContentVariants({ size }), className)}
      {...props}
    >
      {showCloseButton && onClose && (
        <button
          data-slot="sheet-close"
          className="absolute top-4 right-4 p-1 rounded-md hover:bg-gray-100 transition-colors"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={20} />
        </button>
      )}
      {children}
    </div>
  );
}

export { Sheet, SheetOverlay, SheetContent };
