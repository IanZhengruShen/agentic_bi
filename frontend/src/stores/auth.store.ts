/**
 * Authentication state management with Zustand.
 */

import { create } from 'zustand';
import { authService } from '@/services/auth.service';
import type { User, LoginRequest, RegisterRequest } from '@/types/user.types';
import { storage } from '@/lib/storage';

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  hasInitialized: boolean;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  hasInitialized: false,

  // Login action
  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const { user } = await authService.login(credentials);
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed';
      set({ error: errorMessage, isLoading: false, isAuthenticated: false });
      throw error;
    }
  },

  // Register action
  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      await authService.register(data);
      set({ isLoading: false });
      // Note: After registration, user needs to login
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Registration failed';
      set({ error: errorMessage, isLoading: false });
      throw error;
    }
  },

  // Logout action
  logout: async () => {
    set({ isLoading: true });
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  // Load user from storage/API
  loadUser: async () => {
    // Set loading immediately to prevent premature redirects
    set({ isLoading: true });

    if (!authService.isAuthenticated()) {
      set({ user: null, isAuthenticated: false, isLoading: false, hasInitialized: true });
      return;
    }

    try {
      const user = await authService.getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false, hasInitialized: true });
    } catch (error) {
      console.error('Failed to load user:', error);
      storage.clearAuth();
      set({ user: null, isAuthenticated: false, isLoading: false, hasInitialized: true });
    }
  },

  // Clear error
  clearError: () => set({ error: null }),
}));
