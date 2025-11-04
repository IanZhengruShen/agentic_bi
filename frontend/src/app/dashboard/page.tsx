'use client';

import { useAuth } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { BarChart3, Database, Sparkles, Clock } from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();

  const stats = [
    { label: 'Total Queries', value: '0', icon: Database, color: 'text-blue-600' },
    { label: 'Visualizations', value: '0', icon: BarChart3, color: 'text-purple-600' },
    { label: 'AI Insights', value: '0', icon: Sparkles, color: 'text-yellow-600' },
    { label: 'Time Saved', value: '0h', icon: Clock, color: 'text-green-600' },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Welcome back, {user?.full_name || user?.email?.split('@')[0]}!</h1>
        <p className="text-gray-600 mt-1">Here's an overview of your analytics workspace</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className="hover:shadow-lg transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-2">{stat.value}</p>
                  </div>
                  <div className={`p-3 rounded-lg bg-gray-50 ${stat.color}`}>
                    <Icon size={24} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8 text-gray-500">
              <Database className="mx-auto mb-3 text-gray-400" size={48} />
              <p className="text-sm">No recent activity yet</p>
              <p className="text-xs text-gray-400 mt-1">Your queries and insights will appear here</p>
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-4 border border-blue-200 bg-blue-50 rounded-lg">
              <div className="flex items-start space-x-3">
                <Sparkles className="text-blue-600 mt-0.5" size={20} />
                <div>
                  <h4 className="font-medium text-blue-900">Ask a Question</h4>
                  <p className="text-sm text-blue-700 mt-1">
                    Use natural language to query your data
                  </p>
                  <p className="text-xs text-blue-600 mt-2 font-medium">Coming in PR#10</p>
                </div>
              </div>
            </div>

            <div className="p-4 border border-purple-200 bg-purple-50 rounded-lg">
              <div className="flex items-start space-x-3">
                <BarChart3 className="text-purple-600 mt-0.5" size={20} />
                <div>
                  <h4 className="font-medium text-purple-900">Create Visualization</h4>
                  <p className="text-sm text-purple-700 mt-1">
                    Generate charts and insights automatically
                  </p>
                  <p className="text-xs text-purple-600 mt-2 font-medium">Coming in PR#10</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* User Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Account Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Email</p>
              <p className="font-medium text-gray-900 mt-1">{user?.email}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Role</p>
              <p className="font-medium text-gray-900 mt-1 capitalize">{user?.role}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <div className="flex items-center mt-1">
                <div className="w-2 h-2 rounded-full bg-green-500 mr-2"></div>
                <p className="font-medium text-gray-900">Active</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
