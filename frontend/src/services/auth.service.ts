/**
 * Authentication API service.
 *
 * Handles all auth-related API calls.
 */

import apiClient from '@/lib/api-client';
import { storage } from '@/lib/storage';
import type { User, TokenResponse, LoginRequest, RegisterRequest } from '@/types/user.types';

export const authService = {
  /**
   * Login user and store tokens.
   */
  async login(credentials: LoginRequest): Promise<{ user: User; tokens: TokenResponse }> {
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/login', credentials);
    const tokens = response.data;

    // Store tokens
    storage.setAccessToken(tokens.access_token);
    storage.setRefreshToken(tokens.refresh_token);

    // Get user info
    const user = await this.getCurrentUser();

    return { user, tokens };
  },

  /**
   * Register new user.
   */
  async register(data: RegisterRequest): Promise<User> {
    const response = await apiClient.post<User>('/api/v1/auth/register', data);
    return response.data;
  },

  /**
   * Get current user info.
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/api/v1/auth/me');
    const user = response.data;

    // Store user data
    storage.setUser(user);

    return user;
  },

  /**
   * Refresh access token.
   */
  async refreshToken(): Promise<TokenResponse> {
    const refreshToken = storage.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await apiClient.post<TokenResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });

    const tokens = response.data;

    // Store new tokens
    storage.setAccessToken(tokens.access_token);
    storage.setRefreshToken(tokens.refresh_token);

    return tokens;
  },

  /**
   * Logout user.
   */
  async logout(): Promise<void> {
    const refreshToken = storage.getRefreshToken();

    try {
      if (refreshToken) {
        await apiClient.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      }
    } finally {
      // Clear local storage regardless of API call result
      storage.clearAuth();
    }
  },

  /**
   * Check if user is authenticated (has valid token).
   */
  isAuthenticated(): boolean {
    const token = storage.getAccessToken();
    if (!token) return false;

    // Check if token is expired (basic check - decode JWT)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const exp = payload.exp * 1000; // Convert to milliseconds
      return Date.now() < exp;
    } catch {
      return false;
    }
  },
};
