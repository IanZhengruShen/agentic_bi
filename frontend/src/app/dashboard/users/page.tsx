'use client';

/**
 * User Management Page (Admin Only)
 *
 * Allows admins to:
 * - View all users in their company
 * - Search and filter users
 * - Change user roles inline
 * - See user details (email, department, status)
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Users, Search, Shield, AlertCircle, Loader2 } from 'lucide-react';
import { listCompanyUsers, updateUserRole } from '@/services/user.service';
import type { UserProfile, UserRole } from '@/types/user.types';
import { ROLE_METADATA } from '@/types/user.types';
import { useAuthStore } from '@/stores/auth.store';
import { useRouter } from 'next/navigation';

export default function UserManagementPage() {
  const router = useRouter();
  const { user: currentUser } = useAuthStore();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<UserProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);

  // Check if current user is admin
  useEffect(() => {
    if (!currentUser) {
      router.push('/login');
      return;
    }
    if (currentUser.role !== 'admin') {
      toast.error('Access denied', {
        description: 'Only administrators can access user management',
      });
      router.push('/dashboard');
      return;
    }
    loadUsers();
  }, [currentUser, router]);

  // Filter users when search term or role filter changes
  useEffect(() => {
    filterUsers();
  }, [searchTerm, roleFilter, users]);

  const loadUsers = async () => {
    try {
      setIsLoading(true);
      const userList = await listCompanyUsers();
      setUsers(userList);
      setFilteredUsers(userList);
    } catch (error: any) {
      console.error('Failed to load users:', error);
      toast.error('Failed to load users', {
        description: error.response?.data?.detail || 'Please try again',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const filterUsers = () => {
    let filtered = [...users];

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (user) =>
          user.email.toLowerCase().includes(term) ||
          user.full_name?.toLowerCase().includes(term) ||
          user.department?.toLowerCase().includes(term)
      );
    }

    // Apply role filter
    if (roleFilter !== 'all') {
      filtered = filtered.filter((user) => user.role === roleFilter);
    }

    setFilteredUsers(filtered);
  };

  const handleRoleChange = async (userId: string, newRole: UserRole) => {
    const targetUser = users.find((u) => u.id === userId);
    if (!targetUser) return;

    // Prevent self-demotion
    if (userId === currentUser?.id && newRole !== 'admin') {
      toast.error('Cannot demote yourself', {
        description: 'This is a safety measure to prevent accidental lockouts',
      });
      return;
    }

    try {
      setUpdatingUserId(userId);
      await updateUserRole(userId, { new_role: newRole });

      // Update local state
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      );

      toast.success('Role updated', {
        description: `${targetUser.email} is now ${ROLE_METADATA[newRole].label}`,
      });
    } catch (error: any) {
      console.error('Failed to update role:', error);
      toast.error('Failed to update role', {
        description: error.response?.data?.detail || 'Please try again',
      });
    } finally {
      setUpdatingUserId(null);
    }
  };

  const getRoleBadgeVariant = (role: UserRole) => {
    const variants = {
      admin: 'default',
      analyst: 'secondary',
      viewer: 'outline',
      user: 'outline',
    };
    return variants[role] as 'default' | 'secondary' | 'outline';
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

  if (!currentUser || currentUser.role !== 'admin') {
    return null; // Will redirect in useEffect
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Users className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
            {currentUser?.company_name && (
              <p className="text-sm text-gray-500 mt-1">
                {currentUser.company_name}
              </p>
            )}
          </div>
        </div>
        <p className="text-gray-600">
          Manage user roles and permissions for your company
        </p>
      </div>

      {/* Filters */}
      <Card className="p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search by name, email, or department..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Role Filter */}
          <div className="sm:w-48">
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filter by role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                {(Object.keys(ROLE_METADATA) as UserRole[]).map((role) => (
                  <SelectItem key={role} value={role}>
                    {ROLE_METADATA[role].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Refresh */}
          <Button
            onClick={loadUsers}
            variant="outline"
            className="sm:w-auto"
          >
            Refresh
          </Button>
        </div>

        {/* Stats */}
        <div className="mt-4 pt-4 border-t flex gap-6 text-sm">
          <div>
            <span className="text-gray-600">Total Users:</span>{' '}
            <span className="font-semibold text-gray-900">{users.length}</span>
          </div>
          <div>
            <span className="text-gray-600">Showing:</span>{' '}
            <span className="font-semibold text-gray-900">{filteredUsers.length}</span>
          </div>
        </div>
      </Card>

      {/* Users Table */}
      <Card>
        {filteredUsers.length === 0 ? (
          <div className="p-12 text-center">
            <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No users found
            </h3>
            <p className="text-gray-600 mb-4">
              {searchTerm || roleFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'No users in your company yet'}
            </p>
            {(searchTerm || roleFilter !== 'all') && (
              <Button
                onClick={() => {
                  setSearchTerm('');
                  setRoleFilter('all');
                }}
                variant="outline"
              >
                Clear Filters
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Current Role</TableHead>
                  <TableHead>Change Role</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => (
                  <TableRow key={user.id}>
                    {/* User Info */}
                    <TableCell>
                      <div>
                        <div className="font-medium text-gray-900">
                          {user.full_name || 'N/A'}
                          {user.id === currentUser?.id && (
                            <span className="ml-2 text-xs text-blue-600 font-normal">
                              (You)
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                    </TableCell>

                    {/* Department */}
                    <TableCell>
                      <span className="text-sm text-gray-600">
                        {user.department || '—'}
                      </span>
                    </TableCell>

                    {/* Current Role Badge */}
                    <TableCell>
                      <Badge
                        className={getRoleBadgeColor(user.role)}
                        variant={getRoleBadgeVariant(user.role)}
                      >
                        <Shield className="h-3 w-3 mr-1" />
                        {ROLE_METADATA[user.role].label}
                      </Badge>
                    </TableCell>

                    {/* Role Selector */}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Select
                          value={user.role}
                          onValueChange={(newRole) =>
                            handleRoleChange(user.id, newRole as UserRole)
                          }
                          disabled={updatingUserId === user.id}
                        >
                          <SelectTrigger className="w-[180px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {(Object.keys(ROLE_METADATA) as UserRole[]).map(
                              (role) => (
                                <SelectItem key={role} value={role}>
                                  <div className="flex flex-col">
                                    <span className="font-medium">
                                      {ROLE_METADATA[role].label}
                                    </span>
                                    <span className="text-xs text-gray-500">
                                      {ROLE_METADATA[role].description}
                                    </span>
                                  </div>
                                </SelectItem>
                              )
                            )}
                          </SelectContent>
                        </Select>
                        {updatingUserId === user.id && (
                          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                        )}
                      </div>
                    </TableCell>

                    {/* Status */}
                    <TableCell>
                      <Badge
                        variant={user.is_active ? 'default' : 'outline'}
                        className={
                          user.is_active
                            ? 'bg-green-100 text-green-800 border-green-200'
                            : 'bg-gray-100 text-gray-600 border-gray-200'
                        }
                      >
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* Info Box */}
      <Card className="mt-6 p-4 bg-blue-50 border-blue-200">
        <div className="flex gap-3">
          <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-blue-900 mb-1">Role Management Tips</p>
            <ul className="text-blue-800 space-y-1 list-disc list-inside">
              <li>You cannot demote yourself from admin to prevent lockouts</li>
              <li>Role changes take effect immediately</li>
              <li>Only users in your company are visible here</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
