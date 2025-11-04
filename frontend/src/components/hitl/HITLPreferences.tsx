/**
 * HITLPreferences Component
 *
 * User notification preferences configuration.
 */

'use client';

import { useEffect, useState } from 'react';
import { useHITLStore } from '@/stores/hitl.store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Bell, Loader2, Save, Shield, User as UserIcon } from 'lucide-react';
import { toast } from 'sonner';
import type { NotificationPreferences } from '@/types/hitl.types';
import { userService } from '@/services/user.service';
import type { UserProfile, UserRole } from '@/types/user.types';
import { ROLES } from '@/types/user.types';

export function HITLPreferences() {
  const {
    notificationPreferences,
    fetchNotificationPreferences,
    updateNotificationPreferences,
  } = useHITLStore();

  const [localPreferences, setLocalPreferences] = useState<NotificationPreferences>({
    websocket_enabled: true,
    email_enabled: false,
    slack_enabled: false,
    intervention_types: ['sql_review', 'data_modification', 'high_cost_query'],
  });

  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // User profile state
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [selectedRole, setSelectedRole] = useState<UserRole>('user');

  // Fetch preferences and user profile on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        await fetchNotificationPreferences();

        // Fetch user profile
        const profile = await userService.getCurrentUser();
        setUserProfile(profile);
        setSelectedRole(profile.role);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [fetchNotificationPreferences]);

  // Update local state when store updates
  useEffect(() => {
    if (notificationPreferences) {
      setLocalPreferences(notificationPreferences);
    }
  }, [notificationPreferences]);

  /**
   * Save preferences
   */
  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateNotificationPreferences(localPreferences);
      toast.success('Preferences saved', {
        description: 'Your notification preferences have been updated',
      });
    } catch (error) {
      toast.error('Failed to save preferences', {
        description: 'Please try again',
      });
    } finally {
      setIsSaving(false);
    }
  };

  /**
   * Toggle intervention type
   */
  const toggleInterventionType = (type: string) => {
    setLocalPreferences((prev) => {
      const types = prev.intervention_types.includes(type as any)
        ? prev.intervention_types.filter((t) => t !== type)
        : [...prev.intervention_types, type as any];

      return { ...prev, intervention_types: types };
    });
  };

  /**
   * Send test notification
   */
  const handleTestNotification = async () => {
    try {
      // TODO: Implement backend endpoint for test notifications
      toast.info('Test notification sent', {
        description: 'Check your configured channels',
      });
    } catch (error) {
      toast.error('Failed to send test notification');
    }
  };

  /**
   * Update user role (admin only)
   */
  const handleRoleChange = async () => {
    if (!userProfile) return;

    // Prevent self-demotion from admin
    if (userProfile.role === 'admin' && selectedRole !== 'admin') {
      toast.error('Cannot demote yourself from admin', {
        description: 'This is a safety measure to prevent accidental lockouts',
      });
      setSelectedRole(userProfile.role);
      return;
    }

    setIsSaving(true);
    try {
      await userService.updateRole({
        user_id: userProfile.id,
        new_role: selectedRole,
      });

      // Update local state
      setUserProfile({ ...userProfile, role: selectedRole });

      toast.success('Role updated successfully', {
        description: `Your role has been changed to ${selectedRole}`,
      });
    } catch (error: any) {
      toast.error('Failed to update role', {
        description: error.response?.data?.detail || 'An error occurred',
      });
      // Revert selection
      setSelectedRole(userProfile.role);
    } finally {
      setIsSaving(false);
    }
  };

  /**
   * Get badge color for role
   */
  const getRoleBadgeColor = (role: UserRole) => {
    const roleInfo = ROLES.find((r) => r.value === role);
    return roleInfo?.color || 'gray';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Bell className="h-6 w-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Notification Preferences</h1>
      </div>

      {/* User Profile Card */}
      {userProfile && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <UserIcon className="h-5 w-5" />
              User Profile & Role
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Email */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Email</label>
              <p className="text-sm text-gray-900">{userProfile.email}</p>
            </div>

            {/* Current Role */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Current Role</label>
              <div className="flex items-center gap-3">
                <Badge
                  variant={userProfile.role === 'admin' ? 'default' : 'secondary'}
                  className="text-sm"
                >
                  <Shield className="h-3 w-3 mr-1" />
                  {userProfile.role.toUpperCase()}
                </Badge>
                <span className="text-sm text-gray-600">
                  {ROLES.find((r) => r.value === userProfile.role)?.description}
                </span>
              </div>
            </div>

            {/* Role Selector (Admin Only) */}
            {userProfile.role === 'admin' && (
              <div className="space-y-3 border-t pt-6">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-purple-600" />
                  <label className="text-sm font-medium text-gray-900">
                    Change Role (Admin Only)
                  </label>
                </div>
                <p className="text-xs text-gray-600">
                  As an admin, you can change user roles. Note: You cannot demote yourself from admin.
                </p>

                <div className="flex items-center gap-3">
                  <Select value={selectedRole} onValueChange={(value) => setSelectedRole(value as UserRole)}>
                    <SelectTrigger className="w-64">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLES.map((role) => (
                        <SelectItem key={role.value} value={role.value}>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{role.label}</span>
                            <span className="text-xs text-gray-500">- {role.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {selectedRole !== userProfile.role && (
                    <Button onClick={handleRoleChange} disabled={isSaving} size="sm">
                      {isSaving ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Updating...
                        </>
                      ) : (
                        'Update Role'
                      )}
                    </Button>
                  )}
                </div>

                {selectedRole === 'admin' && userProfile.role !== 'admin' && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-xs text-yellow-700">
                    ⚠️ <strong>Warning:</strong> Granting admin privileges gives full system access.
                  </div>
                )}
              </div>
            )}

            {/* Non-Admin Notice */}
            {userProfile.role !== 'admin' && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs text-gray-600">
                💡 <strong>Note:</strong> Only administrators can change user roles. Contact your admin if you need role adjustments.
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Notification Preferences Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notification Preferences
          </CardTitle>
          <p className="text-sm text-gray-600 mt-2">
            Configure how you receive HITL notifications
          </p>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* WebSocket Notifications */}
          <div className="flex items-center justify-between py-3 border-b">
            <div className="flex-1">
              <label className="font-medium text-gray-900">WebSocket Notifications</label>
              <p className="text-sm text-gray-600 mt-1">
                Real-time browser notifications and modal prompts
              </p>
            </div>
            <Switch
              checked={localPreferences.websocket_enabled}
              onCheckedChange={(checked) =>
                setLocalPreferences((prev) => ({ ...prev, websocket_enabled: checked }))
              }
            />
          </div>

          {/* Email Notifications */}
          <div className="flex items-center justify-between py-3 border-b">
            <div className="flex-1">
              <label className="font-medium text-gray-900">Email Notifications</label>
              <p className="text-sm text-gray-600 mt-1">
                Receive email alerts for interventions
              </p>
            </div>
            <Switch
              checked={localPreferences.email_enabled}
              onCheckedChange={(checked) =>
                setLocalPreferences((prev) => ({ ...prev, email_enabled: checked }))
              }
            />
          </div>

          {/* Slack Notifications */}
          <div className="space-y-3 py-3 border-b">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="font-medium text-gray-900">Slack Notifications</label>
                <p className="text-sm text-gray-600 mt-1">
                  Send alerts to a Slack channel
                </p>
              </div>
              <Switch
                checked={localPreferences.slack_enabled}
                onCheckedChange={(checked) =>
                  setLocalPreferences((prev) => ({ ...prev, slack_enabled: checked }))
                }
              />
            </div>

            {localPreferences.slack_enabled && (
              <div className="ml-0 space-y-2">
                <label className="text-sm font-medium text-gray-700">Slack Channel</label>
                <Input
                  placeholder="#hitl-alerts"
                  value={localPreferences.slack_channel || ''}
                  onChange={(e) =>
                    setLocalPreferences((prev) => ({ ...prev, slack_channel: e.target.value }))
                  }
                  className="max-w-md"
                />
                <p className="text-xs text-gray-500">
                  Enter the channel name (e.g., #alerts or @username)
                </p>
              </div>
            )}
          </div>

          {/* Intervention Types */}
          <div className="space-y-3 py-3">
            <label className="font-medium text-gray-900">Notify for these intervention types:</label>
            <p className="text-sm text-gray-600">
              Select which types of interventions should trigger notifications
            </p>

            <div className="space-y-3 mt-3">
              {[
                { value: 'sql_review', label: 'SQL Review', description: 'Generated SQL needs review before execution' },
                { value: 'data_modification', label: 'Data Modification', description: 'Data changes require approval' },
                { value: 'high_cost_query', label: 'High Cost Query', description: 'Expensive queries need confirmation' },
                { value: 'schema_change', label: 'Schema Change', description: 'Database schema modifications' },
                { value: 'export_approval', label: 'Export Approval', description: 'Data export requests' },
              ].map((type) => (
                <label
                  key={type.value}
                  className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={localPreferences.intervention_types.includes(type.value as any)}
                    onChange={() => toggleInterventionType(type.value)}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-sm text-gray-900">{type.label}</div>
                    <div className="text-xs text-gray-600 mt-0.5">{type.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button
              onClick={handleSave}
              disabled={isSaving}
              className="flex-1"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Preferences
                </>
              )}
            </Button>

            <Button
              onClick={handleTestNotification}
              variant="outline"
              className="flex-1"
            >
              <Bell className="h-4 w-4 mr-2" />
              Send Test Notification
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
