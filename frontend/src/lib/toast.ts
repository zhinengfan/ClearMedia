import { toast } from 'sonner';

/**
 * Toast 工具函数，提供常用的提示操作
 */
export const Toast = {
  /**
   * 显示成功提示
   */
  success: (message: string, options?: { duration?: number }) => {
    return toast.success(message, {
      duration: options?.duration || 4000,
    });
  },

  /**
   * 显示错误提示
   */
  error: (message: string, options?: { duration?: number }) => {
    return toast.error(message, {
      duration: options?.duration || 4000,
    });
  },

  /**
   * 显示警告提示
   */
  warning: (message: string, options?: { duration?: number }) => {
    return toast.warning(message, {
      duration: options?.duration || 4000,
    });
  },

  /**
   * 显示信息提示
   */
  info: (message: string, options?: { duration?: number }) => {
    return toast.info(message, {
      duration: options?.duration || 4000,
    });
  },

  /**
   * 显示普通提示
   */
  message: (message: string, options?: { duration?: number }) => {
    return toast(message, {
      duration: options?.duration || 4000,
    });
  },

  /**
   * 显示加载提示
   */
  loading: (message: string) => {
    return toast.loading(message);
  },

  /**
   * 显示带有操作的提示
   */
  action: (
    message: string,
    options: {
      action: {
        label: string;
        onClick: () => void;
      };
      duration?: number;
    }
  ) => {
    return toast(message, {
      duration: options.duration || 4000,
      action: options.action,
    });
  },

  /**
   * 批量操作结果提示
   */
  batchResult: (
    successCount: number,
    failureCount: number,
    operation: string
  ) => {
    if (failureCount === 0) {
      return Toast.success(`${operation}完成：成功 ${successCount} 个`);
    } else if (successCount === 0) {
      return Toast.error(`${operation}失败：失败 ${failureCount} 个`);
    } else {
      return Toast.warning(
        `${operation}完成：成功 ${successCount} 个，失败 ${failureCount} 个`
      );
    }
  },

  /**
   * 关闭所有提示
   */
  dismiss: () => {
    toast.dismiss();
  },
};
