/**
 * useHITL Hook
 *
 * React hook that connects WebSocket events to HITL store.
 * Listens for HITL-related events and updates store accordingly.
 *
 * Usage:
 * ```typescript
 * // In Chat page component
 * const workflowId = currentConversation?.id;
 * useHITL(workflowId);
 * ```
 */

import { useEffect, useRef } from 'react';
import { websocketService, WorkflowEventType } from '@/services/websocket.service';
import { useHITLStore } from '@/stores/hitl.store';
import type { WorkflowEvent } from '@/services/websocket.service';

/**
 * Hook to listen for HITL WebSocket events and update store
 *
 * @param workflowId - Current workflow ID to subscribe to (nullable)
 */
export function useHITL(workflowId: string | null | undefined) {
  const { setPendingRequest, updateTimeRemaining, clearPendingRequest } = useHITLStore();
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!workflowId) {
      console.log('[useHITL] No workflow ID provided, skipping event listeners');
      return;
    }

    console.log('[useHITL] Setting up HITL event listeners for workflow:', workflowId);

    /**
     * Handle all HITL-related events
     */
    const handleHITLEvent = (event: WorkflowEvent) => {
      console.log('[useHITL] HITL event:', event.event_type, event);

      // Handle human_input.required
      if (event.event_type === WorkflowEventType.HUMAN_INPUT_REQUIRED && event.data) {
        const request = {
          request_id: event.data.request_id,
          workflow_id: event.workflow_id,
          conversation_id: event.conversation_id,
          intervention_type: event.data.intervention_type,
          context: event.data.context,
          options: event.data.options,
          timeout_seconds: event.data.timeout_seconds,
          timeout_at: event.data.timeout_at,
          requested_at: event.data.requested_at || event.timestamp,
          status: 'pending' as const,
          required: true,
        };

        setPendingRequest(request);
        startCountdown(request.timeout_seconds);
      }

      // Handle human_input.received
      if (event.event_type === WorkflowEventType.HUMAN_INPUT_RECEIVED) {
        clearPendingRequest();
        stopCountdown();
      }

      // Handle human_input.timeout
      if (event.event_type === WorkflowEventType.HUMAN_INPUT_TIMEOUT) {
        clearPendingRequest();
        stopCountdown();
      }
    };

    // Register event handler
    websocketService.on(workflowId, handleHITLEvent);

    // Cleanup on unmount or workflow change
    return () => {
      console.log('[useHITL] Cleaning up HITL event listeners for workflow:', workflowId);
      stopCountdown();
      websocketService.off(workflowId, handleHITLEvent);
    };
  }, [workflowId, setPendingRequest, clearPendingRequest]);

  /**
   * Start countdown timer (decrements every second)
   */
  const startCountdown = (seconds: number) => {
    console.log('[useHITL] Starting countdown:', seconds, 'seconds');
    stopCountdown(); // Clear any existing timer

    countdownIntervalRef.current = setInterval(() => {
      updateTimeRemaining((prev) => {
        const next = prev - 1;
        if (next <= 0) {
          console.log('[useHITL] Countdown reached zero');
          stopCountdown();
          return 0;
        }
        return next;
      });
    }, 1000);
  };

  /**
   * Stop countdown timer
   */
  const stopCountdown = () => {
    if (countdownIntervalRef.current) {
      console.log('[useHITL] Stopping countdown');
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
  };
}
