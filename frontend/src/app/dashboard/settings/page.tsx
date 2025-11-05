'use client';

/**
 * Main Settings Page
 *
 * Unified settings page with tabs for different setting categories:
 * - Profile & Account: User information, role, security
 * - Chart Preferences: Chart styling
 * - Notifications: Notification preferences (future)
 */

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { User, BarChart3, Bell } from 'lucide-react';
import { ProfileAccountSettings } from '@/components/settings/ProfileAccountSettings';
import { ChartPreferencesSettings } from '@/components/settings/ChartPreferencesSettings';

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState('profile');

  // Support ?tab=charts query parameter for deep linking
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam && ['profile', 'charts', 'notifications'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50 p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Settings
          </h1>
          <p className="text-gray-600">
            Manage your profile, account, and application preferences
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-grid mb-6">
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User size={16} />
              <span className="hidden sm:inline">Profile & Account</span>
              <span className="sm:hidden">Profile</span>
            </TabsTrigger>
            <TabsTrigger value="charts" className="flex items-center gap-2">
              <BarChart3 size={16} />
              <span className="hidden sm:inline">Chart Preferences</span>
              <span className="sm:hidden">Charts</span>
            </TabsTrigger>
            <TabsTrigger value="notifications" className="flex items-center gap-2" disabled>
              <Bell size={16} />
              <span className="hidden sm:inline">Notifications</span>
              <span className="sm:hidden">Notify</span>
              <span className="text-xs bg-gray-200 px-1.5 py-0.5 rounded ml-1">Soon</span>
            </TabsTrigger>
          </TabsList>

          {/* Profile & Account Tab */}
          <TabsContent value="profile">
            <ProfileAccountSettings />
          </TabsContent>

          {/* Chart Preferences Tab */}
          <TabsContent value="charts">
            <ChartPreferencesSettings />
          </TabsContent>

          {/* Notifications Tab (Future) */}
          <TabsContent value="notifications">
            <div className="text-center py-12 text-gray-500">
              Notification settings coming soon...
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
