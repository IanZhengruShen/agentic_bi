/**
 * Authentication hook for components.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth.store';

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, login, logout, register, loadUser } = useAuthStore();

  useEffect(() => {
    // Load user on mount if not already loaded
    if (!user && !isLoading) {
      loadUser();
    }
  }, [user, isLoading, loadUser]);

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    register,
  };
}

export function useProtectedRoute() {
  const router = useRouter();
  const { isAuthenticated, isLoading, hasInitialized, loadUser } = useAuthStore();

  useEffect(() => {
    // Only load user once on mount
    if (!hasInitialized) {
      loadUser();
    }
  }, [hasInitialized, loadUser]);

  useEffect(() => {
    // Only redirect after initialization is complete
    if (hasInitialized && !isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, hasInitialized, router]);

  return { isAuthenticated, isLoading };
}
