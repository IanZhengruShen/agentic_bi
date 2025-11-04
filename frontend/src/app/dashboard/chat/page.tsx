'use client';

import { useEffect } from 'react';
import { useConversationStore } from '@/stores/conversation.store';
import ChatMessageList from '@/components/chat/ChatMessageList';
import ChatInput from '@/components/chat/ChatInput';
import { Button } from '@/components/ui/button';
import { PlusCircle } from 'lucide-react';

export default function ChatPage() {
  const {
    currentConversation,
    startNewConversation,
    availableDatabases,
    fetchDatabases
  } = useConversationStore();

  // Fetch databases on mount
  useEffect(() => {
    fetchDatabases();
  }, [fetchDatabases]);

  // Start conversation once databases are loaded
  useEffect(() => {
    // Start a new conversation with first available database
    if (!currentConversation && availableDatabases.length > 0) {
      startNewConversation(availableDatabases[0].name);
    }
  }, [availableDatabases, currentConversation, startNewConversation]);

  const handleNewChat = () => {
    const defaultDb = availableDatabases.length > 0
      ? availableDatabases[0].name
      : currentConversation?.database || '';
    startNewConversation(defaultDb);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {currentConversation?.title || 'Chat with AI Agent'}
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              Ask questions about your data in natural language
            </p>
          </div>
          <Button onClick={handleNewChat} variant="outline">
            <PlusCircle size={18} className="mr-2" />
            New Chat
          </Button>
        </div>
      </div>

      {/* Messages */}
      <ChatMessageList />

      {/* Input */}
      <ChatInput />
    </div>
  );
}
