/**
 * HITL (Human-in-the-Loop) Store
 *
 * Zustand store for managing HITL state:
 * - Current pending request (displayed in modal)
 * - Time remaining countdown
 * - Intervention history
 * - Notification preferences
 */

import { create } from 'zustand';
import { hitlService } from '@/services/hitl.service';
import type {
  HITLRequest,
  HITLHistoryItem,
  HITLHistoryFilters,
  NotificationPreferences,
  HITLResponsePayload,
} from '@/types/hitl.types';

interface HITLState {
  // Current pending request (shown in modal)
  pendingRequest: HITLRequest | null;

  // Time remaining for current request (seconds)
  timeRemaining: number;

  // History
  history: HITLHistoryItem[];
  historyFilters: HITLHistoryFilters;
  isLoadingHistory: boolean;

  // Notification preferences
  notificationPreferences: NotificationPreferences | null;

  // Loading/error states
  isSubmitting: boolean;
  error: string | null;

  // Actions
  setPendingRequest: (request: HITLRequest | null) => void;
  setTimeRemaining: (seconds: number) => void;
  updateTimeRemaining: (updater: (prev: number) => number) => void;
  submitResponse: (payload: HITLResponsePayload) => Promise<void>;
  fetchHistory: (filters?: HITLHistoryFilters) => Promise<void>;
  setHistoryFilters: (filters: HITLHistoryFilters) => void;
  fetchNotificationPreferences: () => Promise<void>;
  updateNotificationPreferences: (preferences: NotificationPreferences) => Promise<void>;
  clearPendingRequest: () => void;
  clearError: () => void;
}

export const useHITLStore = create<HITLState>((set, get) => ({
  // Initial state
  pendingRequest: null,
  timeRemaining: 0,
  history: [],
  historyFilters: {},
  isLoadingHistory: false,
  notificationPreferences: null,
  isSubmitting: false,
  error: null,

  /**
   * Set pending request (from WebSocket event)
   */
  setPendingRequest: (request) => {
    set({ pendingRequest: request });

    if (request) {
      // Calculate time remaining from timeout_at
      const timeoutAt = new Date(request.timeout_at).getTime();
      const now = Date.now();
      const timeRemaining = Math.max(0, Math.floor((timeoutAt - now) / 1000));

      console.log('[HITLStore] Setting pending request:', {
        request_id: request.request_id,
        timeRemaining,
        timeout_at: request.timeout_at,
      });

      set({ timeRemaining });
    } else {
      set({ timeRemaining: 0 });
    }
  },

  /**
   * Set time remaining (seconds)
   */
  setTimeRemaining: (seconds) => {
    set({ timeRemaining: seconds });
  },

  /**
   * Update time remaining using an updater function
   */
  updateTimeRemaining: (updater) => {
    set((state) => ({ timeRemaining: updater(state.timeRemaining) }));
  },

  /**
   * Submit response to HITL request
   */
  submitResponse: async (payload) => {
    console.log('[HITLStore] Submitting response:', payload);
    set({ isSubmitting: true, error: null });

    try {
      await hitlService.submitResponse(payload);

      console.log('[HITLStore] Response submitted successfully');

      // Clear pending request on success
      set({
        pendingRequest: null,
        timeRemaining: 0,
        isSubmitting: false,
      });

      // Refresh history in background
      const filters = get().historyFilters;
      get().fetchHistory(filters).catch((err) => {
        console.error('[HITLStore] Failed to refresh history:', err);
      });
    } catch (error: any) {
      console.error('[HITLStore] Failed to submit response:', error);
      set({
        error: error.response?.data?.detail || error.message || 'Failed to submit response',
        isSubmitting: false,
      });
      throw error;
    }
  },

  /**
   * Fetch intervention history with filters
   */
  fetchHistory: async (filters) => {
    console.log('[HITLStore] Fetching history with filters:', filters);
    set({ isLoadingHistory: true, error: null });

    try {
      const history = await hitlService.getHistory(filters);

      console.log('[HITLStore] History fetched:', history.length, 'items');

      set({
        history,
        historyFilters: filters || {},
        isLoadingHistory: false,
      });
    } catch (error: any) {
      console.error('[HITLStore] Failed to fetch history:', error);
      set({
        error: error.response?.data?.detail || error.message || 'Failed to fetch history',
        isLoadingHistory: false,
      });
    }
  },

  /**
   * Set history filters and trigger fetch
   */
  setHistoryFilters: (filters) => {
    console.log('[HITLStore] Setting history filters:', filters);
    set({ historyFilters: filters });
    get().fetchHistory(filters);
  },

  /**
   * Fetch user notification preferences
   */
  fetchNotificationPreferences: async () => {
    console.log('[HITLStore] Fetching notification preferences');

    try {
      const preferences = await hitlService.getNotificationPreferences();

      console.log('[HITLStore] Preferences fetched:', preferences);

      set({ notificationPreferences: preferences });
    } catch (error: any) {
      console.error('[HITLStore] Failed to fetch preferences:', error);
      set({
        error: error.response?.data?.detail || error.message || 'Failed to fetch preferences',
      });
    }
  },

  /**
   * Update user notification preferences
   */
  updateNotificationPreferences: async (preferences) => {
    console.log('[HITLStore] Updating notification preferences:', preferences);

    try {
      const updated = await hitlService.updateNotificationPreferences(preferences);

      console.log('[HITLStore] Preferences updated:', updated);

      set({ notificationPreferences: updated });
    } catch (error: any) {
      console.error('[HITLStore] Failed to update preferences:', error);
      set({
        error: error.response?.data?.detail || error.message || 'Failed to update preferences',
      });
      throw error;
    }
  },

  /**
   * Clear pending request
   */
  clearPendingRequest: () => {
    console.log('[HITLStore] Clearing pending request');
    set({ pendingRequest: null, timeRemaining: 0 });
  },

  /**
   * Clear error
   */
  clearError: () => {
    set({ error: null });
  },
}));
