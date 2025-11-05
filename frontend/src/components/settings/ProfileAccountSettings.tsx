'use client';

/**
 * Combined Profile & Account Settings Component
 *
 * Allows users to manage their profile and account:
 * - Profile: Name, email, department, role
 * - Role Management: Admin can change user roles
 * - Security: Change password
 * - Danger Zone: Account deletion
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import { User, Shield, Lock, AlertTriangle } from 'lucide-react';
import {
  getCurrentUserProfile,
  updateUserProfile,
  updateUserRole,
  changePassword,
} from '@/services/user.service';
import type { UserProfile, UserRole } from '@/types/user.types';
import { ROLE_METADATA } from '@/types/user.types';

export function ProfileAccountSettings() {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isChangingRole, setIsChangingRole] = useState(false);

  // Form states
  const [fullName, setFullName] = useState('');
  const [department, setDepartment] = useState('');
  const [selectedRole, setSelectedRole] = useState<UserRole | ''>('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Load user profile on mount
  useEffect(() => {
    loadUserProfile();
  }, []);

  const loadUserProfile = async () => {
    try {
      setIsLoading(true);
      const profile = await getCurrentUserProfile();
      setUserProfile(profile);
      setFullName(profile.full_name || '');
      setDepartment(profile.department || '');
      setSelectedRole(profile.role);
    } catch (error) {
      console.error('Failed to load user profile:', error);
      toast.error('Failed to load profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    if (!userProfile) return;

    try {
      setIsSavingProfile(true);
      const updatedProfile = await updateUserProfile({
        full_name: fullName || undefined,
        department: department || undefined,
      });
      setUserProfile(updatedProfile);
      toast.success('Profile updated successfully');
    } catch (error) {
      console.error('Failed to update profile:', error);
      toast.error('Failed to update profile');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangeRole = async () => {
    if (!userProfile || !selectedRole) return;

    // Prevent self-demotion from admin
    if (userProfile.role === 'admin' && selectedRole !== 'admin') {
      toast.error('Cannot demote yourself from admin', {
        description: 'This is a safety measure to prevent accidental lockouts',
      });
      setSelectedRole(userProfile.role);
      return;
    }

    try {
      setIsChangingRole(true);
      await updateUserRole({
        user_id: userProfile.id,
        new_role: selectedRole,
      });

      // Update local state
      setUserProfile({ ...userProfile, role: selectedRole });
      toast.success(`Role updated to ${ROLE_METADATA[selectedRole].label}`);
    } catch (error: any) {
      console.error('Failed to update role:', error);
      toast.error(error.response?.data?.detail || 'Failed to update role');
      setSelectedRole(userProfile.role); // Reset to original
    } finally {
      setIsChangingRole(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error('Please fill in all password fields');
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    try {
      setIsChangingPassword(true);
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });

      // Clear form
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      toast.success('Password changed successfully');
    } catch (error: any) {
      console.error('Failed to change password:', error);
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const getRoleBadgeColor = (role: UserRole) => {
    const colors = {
      admin: 'bg-purple-100 text-purple-800 border-purple-200',
      analyst: 'bg-blue-100 text-blue-800 border-blue-200',
      viewer: 'bg-gray-100 text-gray-800 border-gray-200',
      user: 'bg-green-100 text-green-800 border-green-200',
    };
    return colors[role];
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (!userProfile) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Failed to load profile</p>
        <Button onClick={loadUserProfile} className="mt-4">Retry</Button>
      </div>
    );
  }

  const isAdmin = userProfile.role === 'admin';
  const roleChanged = selectedRole !== userProfile.role;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Profile & Account
        </h2>
        <p className="text-gray-600">
          Manage your personal information, role, and security settings
        </p>
      </div>

      <div className="space-y-6">
        {/* User Profile */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <User size={18} />
            Profile Information
          </h3>

          <div className="space-y-4">
            {/* Email (read-only) */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={userProfile.email}
                disabled
                className="bg-gray-50"
              />
              <p className="text-xs text-gray-500">
                Email cannot be changed. Contact support if needed.
              </p>
            </div>

            {/* Full Name */}
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <Input
                id="fullName"
                placeholder="John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>

            {/* Department */}
            <div className="space-y-2">
              <Label htmlFor="department">Department</Label>
              <Input
                id="department"
                placeholder="Engineering"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              />
            </div>

            {/* Save Button */}
            <div className="pt-2">
              <Button
                onClick={handleSaveProfile}
                disabled={isSavingProfile}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isSavingProfile ? 'Saving...' : 'Save Profile'}
              </Button>
            </div>
          </div>
        </Card>

        {/* Role Management */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Shield size={18} />
            Role & Permissions
          </h3>

          <div className="space-y-4">
            {/* Current Role */}
            <div>
              <Label className="mb-2 block">Current Role</Label>
              <div className="flex items-center gap-3">
                <span
                  className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium border ${getRoleBadgeColor(
                    userProfile.role
                  )}`}
                >
                  {ROLE_METADATA[userProfile.role].label}
                </span>
                <span className="text-sm text-gray-600">
                  {ROLE_METADATA[userProfile.role].description}
                </span>
              </div>
            </div>

            {/* Admin-Only: Change Role */}
            {isAdmin ? (
              <div className="border-t pt-4 mt-4">
                <Label className="mb-2 block font-semibold">
                  Change Role (Admin Only)
                </Label>
                <p className="text-sm text-gray-600 mb-3">
                  As an admin, you can change your role. Be careful with role changes.
                </p>

                <div className="flex items-end gap-3">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor="roleSelect">Select Role</Label>
                    <Select
                      value={selectedRole}
                      onValueChange={(value) => setSelectedRole(value as UserRole)}
                    >
                      <SelectTrigger id="roleSelect">
                        <SelectValue placeholder="Select a role" />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(ROLE_METADATA) as UserRole[]).map((role) => (
                          <SelectItem key={role} value={role}>
                            <div className="flex flex-col">
                              <span className="font-medium">{ROLE_METADATA[role].label}</span>
                              <span className="text-xs text-gray-500">
                                {ROLE_METADATA[role].description}
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={handleChangeRole}
                    disabled={!roleChanged || isChangingRole}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {isChangingRole ? 'Updating...' : 'Update Role'}
                  </Button>
                </div>

                {selectedRole !== 'admin' && userProfile.role === 'admin' && (
                  <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-md">
                    <p className="text-sm text-amber-800 flex items-center gap-2">
                      <AlertTriangle size={14} />
                      Warning: You cannot demote yourself from admin to prevent lockouts.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="border-t pt-4 mt-4">
                <p className="text-sm text-gray-600 flex items-center gap-2">
                  💡 Only administrators can change user roles. Contact your admin if you need
                  role adjustments.
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* Password Change */}
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
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="newPassword">New Password</Label>
              <Input
                id="newPassword"
                type="password"
                placeholder="Enter new password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
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
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
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

        {/* Danger Zone */}
        <Card className="p-6 border-red-200 bg-red-50">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-red-900">
            <AlertTriangle size={18} />
            Danger Zone
          </h3>

          <div className="space-y-4">
            <div>
              <p className="text-sm text-red-900 mb-1 font-medium">Delete Account</p>
              <p className="text-xs text-red-700 mb-3">
                Once you delete your account, there is no going back. All your data,
                conversations, and settings will be permanently deleted.
              </p>
              <Button
                variant="outline"
                className="border-red-300 text-red-700 hover:bg-red-100 hover:text-red-900"
                onClick={() =>
                  toast.error('Account deletion is not yet available. Contact support.')
                }
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
