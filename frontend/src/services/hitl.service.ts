/**
 * HITL (Human-in-the-Loop) Service
 *
 * Handles API calls for HITL operations:
 * - Submit responses to intervention requests
 * - Fetch pending requests for reconnection
 * - Get intervention history
 * - Manage notification preferences
 */

import apiClient from '@/lib/api-client';
import type {
  HITLRequest,
  HITLResponsePayload,
  HITLResponseResult,
  HITLHistoryItem,
  HITLHistoryFilters,
  NotificationPreferences,
  PendingRequestsResponse,
} from '@/types/hitl.types';

class HITLService {
  /**
   * Submit response to a HITL request
   *
   * @param payload - Response payload (action, feedback, etc.)
   * @returns Result with success status
   *
   * @example
   * ```typescript
   * await hitlService.submitResponse({
   *   request_id: 'hitl-123',
   *   action: 'approve',
   *   feedback: 'Looks good!'
   * });
   * ```
   */
  async submitResponse(payload: HITLResponsePayload): Promise<HITLResponseResult> {
    const response = await apiClient.post<HITLResponseResult>(
      '/hitl/respond',
      payload
    );
    return response.data;
  }

  /**
   * Get pending HITL requests for a workflow
   *
   * Useful for reconnection scenarios - check if any interventions
   * are waiting for response.
   *
   * @param workflowId - Workflow ID to check
   * @returns Array of pending requests
   */
  async getPendingRequests(workflowId: string): Promise<HITLRequest[]> {
    const response = await apiClient.get<PendingRequestsResponse>(
      `/hitl/pending/${workflowId}`
    );
    return response.data.requests;
  }

  /**
   * Get HITL intervention history with optional filters
   *
   * @param filters - Optional filters (type, status, date range)
   * @returns Array of history items
   *
   * @example
   * ```typescript
   * const history = await hitlService.getHistory({
   *   intervention_type: 'sql_review',
   *   status: 'approved',
   *   date_from: '2024-11-01'
   * });
   * ```
   */
  async getHistory(filters?: HITLHistoryFilters): Promise<HITLHistoryItem[]> {
    const response = await apiClient.get<HITLHistoryItem[]>('/hitl/history', {
      params: filters,
    });
    return response.data;
  }

  /**
   * Get user's notification preferences
   *
   * @returns Current notification preferences
   */
  async getNotificationPreferences(): Promise<NotificationPreferences> {
    const response = await apiClient.get<NotificationPreferences>(
      '/users/me/notification-preferences'
    );
    return response.data;
  }

  /**
   * Update user's notification preferences
   *
   * @param preferences - New preferences
   * @returns Updated preferences
   *
   * @example
   * ```typescript
   * await hitlService.updateNotificationPreferences({
   *   websocket_enabled: true,
   *   email_enabled: true,
   *   slack_enabled: false,
   *   intervention_types: ['sql_review', 'data_modification']
   * });
   * ```
   */
  async updateNotificationPreferences(
    preferences: NotificationPreferences
  ): Promise<NotificationPreferences> {
    const response = await apiClient.put<NotificationPreferences>(
      '/users/me/notification-preferences',
      preferences
    );
    return response.data;
  }

  /**
   * Cancel a pending HITL request
   *
   * @param requestId - Request ID to cancel
   */
  async cancelRequest(requestId: string): Promise<void> {
    await apiClient.delete(`/hitl/requests/${requestId}`);
  }

  /**
   * Test notification delivery
   *
   * Sends a test notification to verify channels are configured correctly.
   */
  async sendTestNotification(): Promise<void> {
    await apiClient.post('/hitl/test-notification');
  }
}

export const hitlService = new HITLService();
