import { Link, useMatchRoute } from '@tanstack/react-router';
import { Home, FolderOpen, Settings, X } from 'lucide-react';

interface SidebarProps {
  isOpen?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ isOpen = true, onToggle }: SidebarProps) {
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
        fixed left-0 top-0 h-full bg-white border-r border-secondary-200 z-50 transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0 lg:static lg:z-auto
        w-64
      `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-secondary-200">
          <h1 className="text-xl font-bold text-secondary-900">ClearMedia</h1>
          <button
            onClick={onToggle}
            className="p-1 rounded-md hover:bg-secondary-100 lg:hidden"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const isActive = matchRoute({ to: item.to, fuzzy: false });
              const Icon = item.icon;

              return (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className={`
                      flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors duration-200
                      ${
                        isActive
                          ? 'bg-primary-50 text-primary-700 font-medium'
                          : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                      }
                    `}
                    onClick={() => {
                      // Close mobile sidebar on navigation
                      if (window.innerWidth < 1024 && onToggle) {
                        onToggle();
                      }
                    }}
                  >
                    <Icon size={20} />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="absolute bottom-4 left-4 right-4">
          <div className="text-xs text-secondary-500 text-center">
            © 2025 ClearMedia
          </div>
        </div>
      </div>
    </>
  );
}

export default Sidebar;
