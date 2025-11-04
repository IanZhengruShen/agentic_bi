/**
 * User Type Definitions
 *
 * Types for user profile, roles, and permissions.
 */

/**
 * User roles in the system
 */
export type UserRole = 'admin' | 'analyst' | 'viewer' | 'user';

/**
 * User model (from backend)
 */
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  company_id: string | null;
  department: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  created_at: string;
}

/**
 * Token response from authentication endpoints
 */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

/**
 * Login request payload
 */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Registration request payload
 */
export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  department?: string;
  company_name?: string;
}

/**
 * User profile data
 */
export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
  company_id?: string;
  department?: string;
}

/**
 * User profile update payload
 */
export interface UserProfileUpdate {
  full_name?: string;
  department?: string;
}

/**
 * Role update request (admin only)
 */
export interface RoleUpdateRequest {
  user_id: string;
  new_role: UserRole;
}

/**
 * Role update response
 */
export interface RoleUpdateResponse {
  success: boolean;
  message: string;
  user_id: string;
  new_role: UserRole;
}

/**
 * Role metadata
 */
export interface RoleInfo {
  value: UserRole;
  label: string;
  description: string;
  color: string; // Tailwind color class
}

/**
 * Available roles with metadata
 */
export const ROLES: RoleInfo[] = [
  {
    value: 'admin',
    label: 'Administrator',
    description: 'Full system access and user management',
    color: 'purple',
  },
  {
    value: 'analyst',
    label: 'Analyst',
    description: 'Can create and analyze queries, access all data',
    color: 'blue',
  },
  {
    value: 'viewer',
    label: 'Viewer',
    description: 'Read-only access to dashboards and reports',
    color: 'gray',
  },
  {
    value: 'user',
    label: 'User',
    description: 'Standard user access with limited permissions',
    color: 'green',
  },
];
