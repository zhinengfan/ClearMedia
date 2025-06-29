import { Link, useMatchRoute } from '@tanstack/react-router';
import {
  Home,
  FolderOpen,
  Settings,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface SidebarProps {
  isOpen?: boolean;
  onToggle?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Sidebar({
  isOpen = true,
  onToggle,
  collapsed = false,
  onToggleCollapse,
}: SidebarProps) {
  const matchRoute = useMatchRoute();

  const navItems = [
    {
      to: '/',
      label: '首页',
      icon: Home,
    },
    {
      to: '/media',
      label: '媒体管理',
      icon: FolderOpen,
    },
    {
      to: '/settings',
      label: '系统设置',
      icon: Settings,
    },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
        fixed left-0 top-0 h-full bg-gray-50 border-r border-secondary-200 z-50 transition-all duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0 lg:static lg:z-auto
        ${collapsed ? 'w-16' : 'w-64'}
      `}
      >
        {/* Header */}
        <div
          className={`flex items-center ${collapsed ? 'p-4 justify-center' : 'px-4 py-5 justify-between'} border-b border-secondary-200`}
        >
          {!collapsed && (
            <h1 className="text-3xl font-bold text-secondary-900 tracking-tight">
              ClearMedia
            </h1>
          )}

          {/* Desktop collapse button */}
          <button
            onClick={onToggleCollapse}
            className={`hidden lg:block rounded-md hover:bg-gray-200 transition-colors ${collapsed ? 'p-2' : 'p-1'}`}
            title={collapsed ? '展开侧边栏' : '收缩侧边栏'}
          >
            {collapsed ? <ChevronRight size={24} /> : <ChevronLeft size={20} />}
          </button>

          {/* Mobile close button */}
          {!collapsed && (
            <button
              onClick={onToggle}
              className="p-1 rounded-md hover:bg-secondary-100 lg:hidden"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className={collapsed ? 'p-2' : 'p-4'}>
          <ul className="space-y-4">
            {navItems.map((item) => {
              const isActive = matchRoute({ to: item.to, fuzzy: false });
              const Icon = item.icon;

              return (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className={`
                      flex items-center ${collapsed ? 'justify-center px-2 py-3' : 'space-x-3 px-3 py-3'} rounded-lg transition-colors duration-200
                      ${
                        isActive
                          ? 'bg-green-100 text-green-700 font-medium'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }
                    `}
                    title={collapsed ? item.label : undefined}
                    onClick={() => {
                      // Close mobile sidebar on navigation
                      if (window.innerWidth < 1024 && onToggle) {
                        onToggle();
                      }
                    }}
                  >
                    <Icon size={collapsed ? 24 : 20} />
                    {!collapsed && <span>{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        {!collapsed && (
          <div className="absolute bottom-4 left-4 right-4">
            <div className="text-xs text-secondary-500 text-center">
              © 2025 ClearMedia
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default Sidebar;
