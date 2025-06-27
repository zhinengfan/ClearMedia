import {
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router';
import Dashboard from './pages/Dashboard';
import Files from './pages/Files';
import Settings from './pages/Settings';
import RootLayout from './layouts/RootLayout';

// 创建根路由
const rootRoute = createRootRoute({
  component: RootLayout,
});

// 创建首页路由
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Dashboard,
});

// 创建媒体管理路由
const mediaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/media',
  component: Files,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      skip: Number(search?.skip) || 0,
      limit: Number(search?.limit) || 20,
      status: (search?.status as string) || '',
      search: (search?.search as string) || '',
      sort: (search?.sort as string) || 'created_at:desc',
    };
  },
});

// 创建设置路由
const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/settings',
  component: Settings,
});

// 创建路由树
const routeTree = rootRoute.addChildren([
  indexRoute,
  mediaRoute,
  settingsRoute,
]);

// 创建路由器实例
export const router = createRouter({ routeTree });

// 类型安全声明
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
