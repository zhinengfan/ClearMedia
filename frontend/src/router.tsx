import {
  Outlet,
  Link,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';

// 创建根路由
const rootRoute = createRootRoute({
  component: () => (
    <>
      <div className="p-2 flex gap-2 text-lg border-b">
        <Link
          to="/"
          activeProps={{
            className: 'font-bold',
          }}
          activeOptions={{ exact: true }}
        >
          首页
        </Link>{' '}
        <Link
          to="/media"
          activeProps={{
            className: 'font-bold',
          }}
        >
          媒体管理
        </Link>{' '}
        <Link
          to="/settings"
          activeProps={{
            className: 'font-bold',
          }}
        >
          系统设置
        </Link>
      </div>
      <Outlet />
      <TanStackRouterDevtools />
    </>
  ),
});

// 创建首页路由
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: function Index() {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-secondary-900 mb-4">
          Dashboard
        </h1>
        <p className="text-secondary-600">欢迎使用媒体管理系统</p>
      </div>
    );
  },
});

// 创建媒体管理路由
const mediaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/media',
  component: function Media() {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-secondary-900 mb-4">媒体管理</h1>
        <p className="text-secondary-600">管理您的媒体文件</p>
      </div>
    );
  },
});

// 创建设置路由
const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/settings',
  component: function Settings() {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-secondary-900 mb-4">系统设置</h1>
        <p className="text-secondary-600">配置系统参数</p>
      </div>
    );
  },
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
