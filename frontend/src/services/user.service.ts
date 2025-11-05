/**
 * User Service
 *
 * Handles API calls for user profile and role management.
 */

import apiClient from '@/lib/api-client';
import type {
  UserProfile,
  UserProfileUpdate,
  RoleUpdateRequest,
  RoleUpdateResponse,
  PasswordChangeRequest,
} from '@/types/user.types';

const USERS_BASE_URL = '/users';

/**
 * Get current user profile
 */
export const getCurrentUserProfile = async (): Promise<UserProfile> => {
  const response = await apiClient.get<UserProfile>(`${USERS_BASE_URL}/me`);
  return response.data;
};

/**
 * Update current user profile (non-sensitive fields)
 */
export const updateUserProfile = async (
  updates: UserProfileUpdate
): Promise<UserProfile> => {
  const response = await apiClient.put<UserProfile>(
    `${USERS_BASE_URL}/me`,
    updates
  );
  return response.data;
};

/**
 * Update user role (admin only)
 */
export const updateUserRole = async (
  request: RoleUpdateRequest
): Promise<RoleUpdateResponse> => {
  const response = await apiClient.put<RoleUpdateResponse>(
    `${USERS_BASE_URL}/role`,
    request
  );
  return response.data;
};

/**
 * Change password
 */
export const changePassword = async (
  request: PasswordChangeRequest
): Promise<{ message: string }> => {
  const response = await apiClient.put<{ message: string }>(
    `${USERS_BASE_URL}/me/password`,
    request
  );
  return response.data;
};
