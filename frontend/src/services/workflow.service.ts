/**
 * Workflow API service.
 *
 * Basic implementation for PR#9. Will be extended in PR#10-11.
 */

import apiClient from '@/lib/api-client';
import type { WorkflowRequest, WorkflowResponse } from '@/types/workflow.types';

export const workflowService = {
  /**
   * Execute unified workflow.
   */
  async execute(request: WorkflowRequest): Promise<WorkflowResponse> {
    const response = await apiClient.post<WorkflowResponse>('/workflows/execute', request);
    return response.data;
  },

  /**
   * Get workflow status (placeholder - not fully implemented in backend).
   */
  async getStatus(workflowId: string): Promise<any> {
    const response = await apiClient.get(`/workflows/${workflowId}/status`);
    return response.data;
  },
};
