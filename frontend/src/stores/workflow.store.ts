/**
 * Workflow state management.
 *
 * Basic structure for PR#9. Will be fully implemented in PR#10-11.
 */

import { create } from 'zustand';
import type { WorkflowResponse } from '@/types/workflow.types';

interface WorkflowState {
  // Current workflow execution
  currentWorkflow: WorkflowResponse | null;
  isExecuting: boolean;
  error: string | null;

  // Workflow history (future)
  history: WorkflowResponse[];

  // Actions (to be implemented in PR#10)
  setCurrentWorkflow: (workflow: WorkflowResponse | null) => void;
  setIsExecuting: (executing: boolean) => void;
  setError: (error: string | null) => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  currentWorkflow: null,
  isExecuting: false,
  error: null,
  history: [],

  setCurrentWorkflow: (workflow) => set({ currentWorkflow: workflow }),
  setIsExecuting: (executing) => set({ isExecuting: executing }),
  setError: (error) => set({ error: error }),
}));
