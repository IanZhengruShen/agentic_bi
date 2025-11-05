'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, MessageSquare, Settings, Sparkles, Clock, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation: Array<{
  name: string;
  href: string;
  icon: any;
  description: string;
  badge?: string;
}> = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: Home,
    description: 'Overview & stats'
  },
  {
    name: 'Chat',
    href: '/dashboard/chat',
    icon: MessageSquare,
    description: 'Query & analyze'
  },
  {
    name: 'Settings',
    href: '/dashboard/settings',
    icon: Settings,
    description: 'Application settings'
  },
];

const quickLinks = [
  { name: 'Recent Queries', icon: Clock },
  { name: 'AI Insights', icon: Sparkles },
  { name: 'Trending', icon: TrendingUp },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Main Menu</h2>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          // For Settings, match /dashboard/settings and /dashboard/settings/*
          const isActive = item.href === '/dashboard/settings'
            ? pathname.startsWith('/dashboard/settings')
            : pathname === item.href;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center justify-between px-3 py-3 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 shadow-sm'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              )}
            >
              <div className="flex items-center space-x-3">
                <div className={cn(
                  'p-2 rounded-md',
                  isActive ? 'bg-blue-100' : 'bg-gray-100'
                )}>
                  <Icon size={18} className={isActive ? 'text-blue-600' : 'text-gray-600'} />
                </div>
                <div>
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs text-gray-500">{item.description}</div>
                </div>
              </div>
              {item.badge && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-gray-200">
        <div className="px-3 py-2">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Quick Access
          </h3>
          <div className="space-y-2">
            {quickLinks.map((link) => {
              const Icon = link.icon;
              return (
                <button
                  key={link.name}
                  className="w-full flex items-center space-x-2 px-2 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
                >
                  <Icon size={14} />
                  <span>{link.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
