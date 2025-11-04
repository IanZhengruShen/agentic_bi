import { create } from 'zustand';
import { workflowService } from '@/services/workflow.service';
import { databaseService, type Database } from '@/services/database.service';
import type { WorkflowResponse } from '@/types/workflow.types';

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
  workflowResponse?: WorkflowResponse; // For agent messages
  isLoading?: boolean; // For loading states
}

export interface Conversation {
  id: string; // This is the conversation_id for backend
  title: string; // Auto-generated from first message
  messages: Message[];
  database: string; // Current database
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

    // Add user message (optimistic)
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // Add loading message
    const loadingMessage: Message = {
      id: crypto.randomUUID(),
      role: 'agent',
      content: '',
      timestamp: new Date(),
      isLoading: true,
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
        updatedAt: new Date(),
      },
      isLoading: true,
      error: null,
    });

    try {
      // Call backend
      const response = await workflowService.execute({
        query: content,
        database: currentConversation.database,
        conversation_id: currentConversation.id,
        options: {
          auto_visualize: true,
          include_insights: true,
        },
      });

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
