'use client';

import { useEffect, useRef } from 'react';
import { useConversationStore } from '@/stores/conversation.store';
import ChatMessage from './ChatMessage';
import { Sparkles } from 'lucide-react';

export default function ChatMessageList() {
  const { currentConversation } = useConversationStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);

  if (!currentConversation || currentConversation.messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center mx-auto mb-4">
            <Sparkles size={32} className="text-white" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">
            Start a Conversation
          </h3>
          <p className="text-gray-600">
            Ask me anything about your data. I can help you analyze, visualize, and understand your data.
          </p>
          <div className="mt-6 space-y-2 text-sm text-gray-500">
            <p>💡 Try asking:</p>
            <p>&quot;Show me total sales by region&quot;</p>
            <p>&quot;What were the top 10 products last quarter?&quot;</p>
            <p>&quot;Compare Q1 and Q2 revenue&quot;</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4">
      {currentConversation.messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}
