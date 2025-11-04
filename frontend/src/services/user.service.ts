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
} from '@/types/user.types';

class UserService {
  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<UserProfile> {
    const response = await apiClient.get<UserProfile>('/users/me');
    return response.data;
  }

  /**
   * Update user profile
   */
  async updateProfile(profile: UserProfileUpdate): Promise<UserProfile> {
    const response = await apiClient.put<UserProfile>('/users/me', profile);
    return response.data;
  }

  /**
   * Update user role (admin only)
   */
  async updateRole(request: RoleUpdateRequest): Promise<RoleUpdateResponse> {
    const response = await apiClient.put<RoleUpdateResponse>('/users/role', request);
    return response.data;
  }
}

export const userService = new UserService();
