import { create } from 'zustand';
import { workflowService } from '@/services/workflow.service';
import { databaseService, type Database } from '@/services/database.service';
import { websocketService, WorkflowEventType, type WorkflowEvent } from '@/services/websocket.service';
import type { WorkflowResponse } from '@/types/workflow.types';

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
  workflowResponse?: WorkflowResponse; // For agent messages
  isLoading?: boolean; // For loading states
  progress?: {
    stage: string;
    message: string;
  };
}

export interface Conversation {
  id: string; // This is the conversation_id for backend
  title: string; // Auto-generated from first message
  messages: Message[];
  database: string; // Current database
  currentWorkflowId?: string; // Track current active workflow
  createdAt: Date;
  updatedAt: Date;
}

interface ConversationState {
  // State
  currentConversation: Conversation | null;
  conversations: Conversation[]; // History of all conversations
  isLoading: boolean;
  error: string | null;
  availableDatabases: Database[];
  isLoadingDatabases: boolean;

  // Actions
  startNewConversation: (database: string) => void;
  sendMessage: (content: string) => Promise<void>;
  loadConversation: (conversationId: string) => void;
  deleteConversation: (conversationId: string) => void;
  setDatabase: (database: string) => void;
  clearError: () => void;
  fetchDatabases: () => Promise<void>;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  currentConversation: null,
  conversations: [],
  isLoading: false,
  error: null,
  availableDatabases: [],
  isLoadingDatabases: false,

  startNewConversation: (database: string) => {
    const newConversation: Conversation = {
      id: crypto.randomUUID(), // Will be returned from backend
      title: 'New Conversation',
      messages: [],
      database,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    set({
      currentConversation: newConversation,
      conversations: [newConversation, ...get().conversations],
    });
  },

  sendMessage: async (content: string) => {
    const { currentConversation } = get();
    if (!currentConversation) {
      set({ error: 'No active conversation' });
      return;
    }

    // Generate workflow ID
    const workflowId = crypto.randomUUID();

    // Add user message (optimistic)
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // Add loading message with initial progress
    const loadingMessage: Message = {
      id: crypto.randomUUID(),
      role: 'agent',
      content: '',
      timestamp: new Date(),
      isLoading: true,
      progress: {
        stage: 'starting',
        message: 'Starting workflow...'
      }
    };

    const updatedMessages = [
      ...currentConversation.messages,
      userMessage,
      loadingMessage,
    ];

    set({
      currentConversation: {
        ...currentConversation,
        messages: updatedMessages,
        currentWorkflowId: workflowId, // Track current workflow
        updatedAt: new Date(),
      },
      isLoading: true,
      error: null,
    });

    try {
      // Connect WebSocket if not connected (ignore errors - app works without WebSocket)
      if (!websocketService.isConnected()) {
        try {
          await websocketService.connect();
        } catch (error) {
          console.warn('[Chat] WebSocket connection failed, continuing without real-time updates');
        }
      }

      // Subscribe to workflow events (only if connected)
      if (websocketService.isConnected()) {
        websocketService.subscribe(workflowId);
      }

      // Set up event handler for real-time progress updates
      const handleEvent = (event: WorkflowEvent) => {
        const { currentConversation } = get();
        if (!currentConversation) return;

        // Find loading message
        const messageIndex = currentConversation.messages.findIndex(
          m => m.id === loadingMessage.id
        );
        if (messageIndex === -1) return;

        // Debug: Log the event to understand structure
        console.log('[Progress] Event:', event.event_type, 'Stage:', event.stage, 'Agent:', event.agent, 'Message:', event.message);

        // Update progress based on event type
        let progressMessage = '';
        let stage = '';

        switch (event.event_type) {
          case WorkflowEventType.WORKFLOW_STARTED:
            stage = 'started';
            progressMessage = event.message || 'Workflow started...';
            break;
          case WorkflowEventType.STAGE_STARTED:
            stage = event.stage || 'processing';
            // Use backend message if available, otherwise use our detailed message
            progressMessage = event.message || getStageMessage(event.stage);
            break;
          case WorkflowEventType.AGENT_STARTED:
            stage = event.agent || 'agent';
            // Use our detailed agent message (more informative than backend's generic message)
            progressMessage = getAgentMessage(event.agent);
            console.log('[Progress] Agent detected:', event.agent, 'Message:', progressMessage);
            break;
          case WorkflowEventType.STAGE_COMPLETED:
            // Don't update on stage completion, wait for next stage
            return;
          case WorkflowEventType.AGENT_COMPLETED:
            // Don't update on agent completion, wait for next event
            return;
          case WorkflowEventType.WORKFLOW_COMPLETED:
            // Will be handled by API response
            return;
          case WorkflowEventType.WORKFLOW_FAILED:
            stage = 'failed';
            progressMessage = event.error || 'Workflow failed';
            break;
          default:
            return;
        }

        // Update loading message with progress
        const updatedMessages = [...currentConversation.messages];
        updatedMessages[messageIndex] = {
          ...updatedMessages[messageIndex],
          progress: {
            stage,
            message: progressMessage
          }
        };

        set({
          currentConversation: {
            ...currentConversation,
            messages: updatedMessages,
          }
        });
      };

      // Register event handler (only if connected)
      if (websocketService.isConnected()) {
        websocketService.on(workflowId, handleEvent);
      }

      // Execute workflow via REST API
      const response = await workflowService.execute({
        workflow_id: workflowId,
        query: content,
        database: currentConversation.database,
        conversation_id: currentConversation.id,
        options: {
          auto_visualize: true,
          include_insights: true,
        },
      });

      // Cleanup WebSocket subscription
      websocketService.off(workflowId, handleEvent);
      websocketService.unsubscribe(workflowId);

      // Update conversation_id from backend if first message
      const conversationId = response.metadata.conversation_id;

      // Create agent response message
      const agentMessage: Message = {
        id: crypto.randomUUID(),
        role: 'agent',
        content: generateAgentSummary(response),
        timestamp: new Date(),
        workflowResponse: response,
      };

      // Remove loading message, add real response
      const finalMessages = [
        ...currentConversation.messages,
        userMessage,
        agentMessage,
      ];

      // Generate title from first message if needed
      const title =
        currentConversation.messages.length === 0
          ? generateTitle(content)
          : currentConversation.title;

      set({
        currentConversation: {
          ...currentConversation,
          id: conversationId, // Update with backend ID
          title,
          messages: finalMessages,
          updatedAt: new Date(),
        },
        isLoading: false,
      });
    } catch (error: any) {
      // Cleanup on error
      websocketService.unsubscribe(workflowId);

      // Remove loading message, show error
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: 'agent',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date(),
      };

      set({
        currentConversation: {
          ...currentConversation,
          messages: [...currentConversation.messages, userMessage, errorMessage],
          updatedAt: new Date(),
        },
        isLoading: false,
        error: error.message || 'Failed to send message',
      });
    }
  },

  loadConversation: (conversationId: string) => {
    const conversation = get().conversations.find((c) => c.id === conversationId);
    if (conversation) {
      set({ currentConversation: conversation });
    }
  },

  deleteConversation: (conversationId: string) => {
    set({
      conversations: get().conversations.filter((c) => c.id !== conversationId),
      currentConversation:
        get().currentConversation?.id === conversationId
          ? null
          : get().currentConversation,
    });
  },

  setDatabase: (database: string) => {
    const { currentConversation } = get();
    if (currentConversation) {
      set({
        currentConversation: {
          ...currentConversation,
          database,
        },
      });
    }
  },

  clearError: () => set({ error: null }),

  fetchDatabases: async () => {
    set({ isLoadingDatabases: true });
    try {
      const databases = await databaseService.getAccessibleDatabases();
      set({
        availableDatabases: databases,
        isLoadingDatabases: false
      });
    } catch (error: any) {
      console.error('Failed to fetch databases:', error);
      set({
        availableDatabases: [],
        isLoadingDatabases: false,
        error: error.message || 'Failed to fetch databases'
      });
    }
  },
}));

// Helper functions
function generateAgentSummary(response: WorkflowResponse): string {
  const { analysis, insights } = response;

  if (analysis && analysis.row_count > 0) {
    return `I found ${analysis.row_count} rows. ${insights[0] || 'Here are the results:'}`;
  }

  return 'Here are the results from your query.';
}

function generateTitle(firstMessage: string): string {
  // Take first 50 chars or first sentence
  const truncated = firstMessage.length > 50
    ? firstMessage.substring(0, 50) + '...'
    : firstMessage;
  return truncated;
}

/**
 * Get user-friendly message for workflow stage
 */
function getStageMessage(stage?: string): string {
  switch (stage) {
    case 'analysis':
      return 'Analyzing your query and understanding intent...';
    case 'deciding':
      return 'Planning next steps based on analysis...';
    case 'visualizing':
      return 'Generating visualization with optimal chart type...';
    case 'finalizing':
      return 'Preparing final results and insights...';
    default:
      return 'Processing your request...';
  }
}

/**
 * Get user-friendly message for agent activity with detailed descriptions
 */
function getAgentMessage(agent?: string): string {
  switch (agent) {
    case 'analysis':
      return '🔍 Analysis Agent: Exploring database schema, generating SQL, and fetching data...';
    case 'visualization':
      return '📊 Visualization Agent: Selecting chart type and creating interactive visualizations...';
    default:
      return 'AI Agent processing your request...';
  }
}
