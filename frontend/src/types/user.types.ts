/**
 * User and authentication type definitions.
 *
 * These types mirror the backend Pydantic schemas.
 */

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  company_id: string | null;
  department: string | null;
  role: 'admin' | 'analyst' | 'viewer' | 'user';
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  department?: string;
  company_name?: string;
}

export type UserRole = 'admin' | 'analyst' | 'viewer' | 'user';

export interface RoleMetadata {
  label: string;
  description: string;
  color: string;
  permissions: string;
}

export const ROLE_METADATA: Record<UserRole, RoleMetadata> = {
  admin: {
    label: 'Administrator',
    description: 'Full system access and user management',
    color: 'purple',
    permissions: 'All permissions',
  },
  analyst: {
    label: 'Analyst',
    description: 'Can create and analyze queries, access all data',
    color: 'blue',
    permissions: 'Query + Analysis',
  },
  viewer: {
    label: 'Viewer',
    description: 'Read-only access to dashboards and reports',
    color: 'gray',
    permissions: 'Read-only',
  },
  user: {
    label: 'User',
    description: 'Standard user access with limited permissions',
    color: 'green',
    permissions: 'Basic access',
  },
};

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
  company_id?: string;
  department?: string;
}

export interface UserProfileUpdate {
  full_name?: string;
  department?: string;
}

export interface RoleUpdateRequest {
  user_id: string;
  new_role: UserRole;
}

export interface RoleUpdateResponse {
  success: boolean;
  message: string;
  user_id: string;
  new_role: UserRole;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}
