'use client';

/**
 * Account Settings Component
 *
 * Allows users to manage account security and preferences:
 * - Change password
 * - Two-factor authentication
 * - Session management
 * - Account deletion
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Shield, Lock, Smartphone, AlertTriangle, LogOut } from 'lucide-react';

export function AccountSettings() {
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const handleChangePassword = async () => {
    setIsChangingPassword(true);
    // TODO: Implement password change API call
    setTimeout(() => {
      toast.success('Password changed successfully');
      setIsChangingPassword(false);
    }, 1000);
  };

  const handleLogoutAllSessions = () => {
    toast.info('Logged out from all other sessions');
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Account & Security
        </h2>
        <p className="text-gray-600">
          Manage your account security and authentication settings
        </p>
      </div>

      <div className="space-y-6">
        {/* Password */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Lock size={18} />
            Change Password
          </h3>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="currentPassword">Current Password</Label>
              <Input
                id="currentPassword"
                type="password"
                placeholder="Enter current password"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="newPassword">New Password</Label>
              <Input
                id="newPassword"
                type="password"
                placeholder="Enter new password"
              />
              <p className="text-xs text-gray-500">
                Must be at least 8 characters with a mix of letters, numbers, and symbols
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm New Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm new password"
              />
            </div>

            <div className="pt-2">
              <Button
                onClick={handleChangePassword}
                disabled={isChangingPassword}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isChangingPassword ? 'Changing...' : 'Change Password'}
              </Button>
            </div>
          </div>
        </Card>

        {/* Two-Factor Authentication */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Smartphone size={18} />
            Two-Factor Authentication
          </h3>

          <div className="space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm text-gray-700 mb-1 font-medium">
                  2FA Status: <span className="text-red-600">Disabled</span>
                </p>
                <p className="text-xs text-gray-500">
                  Add an extra layer of security to your account by requiring a verification code in addition to your password.
                </p>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full sm:w-auto"
              onClick={() => toast.info('2FA setup coming soon')}
            >
              Enable Two-Factor Authentication
            </Button>
          </div>
        </Card>

        {/* Active Sessions */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Shield size={18} />
            Active Sessions
          </h3>

          <div className="space-y-4">
            <div className="text-sm text-gray-700">
              <div className="flex items-center justify-between py-3 border-b">
                <div>
                  <p className="font-medium">Current Session</p>
                  <p className="text-xs text-gray-500">Chrome on macOS • Amsterdam, Netherlands</p>
                  <p className="text-xs text-gray-500">Last active: Just now</p>
                </div>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">Active</span>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={handleLogoutAllSessions}
              className="w-full sm:w-auto flex items-center gap-2"
            >
              <LogOut size={14} />
              Logout All Other Sessions
            </Button>
          </div>
        </Card>

        {/* Danger Zone */}
        <Card className="p-6 border-red-200 bg-red-50">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-red-900">
            <AlertTriangle size={18} />
            Danger Zone
          </h3>

          <div className="space-y-4">
            <div>
              <p className="text-sm text-red-900 mb-1 font-medium">
                Delete Account
              </p>
              <p className="text-xs text-red-700 mb-3">
                Once you delete your account, there is no going back. All your data, conversations, and settings will be permanently deleted.
              </p>
              <Button
                variant="outline"
                className="border-red-300 text-red-700 hover:bg-red-100 hover:text-red-900"
                onClick={() => toast.error('Account deletion is not yet available. Contact support.')}
              >
                Delete Account
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
