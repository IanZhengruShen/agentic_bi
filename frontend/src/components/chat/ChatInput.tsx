'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { useConversationStore } from '@/stores/conversation.store';
import { Button } from '@/components/ui/button';
import { Send, Database } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export default function ChatInput() {
  const {
    currentConversation,
    sendMessage,
    setDatabase,
    isLoading,
    availableDatabases,
    isLoadingDatabases
  } = useConversationStore();
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    await sendMessage(input.trim());
    setInput('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);

    // Auto-expand textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="max-w-4xl mx-auto space-y-3">
        {/* Database Selector */}
        <div className="flex items-center space-x-2">
          <Database size={16} className="text-gray-500" />
          <Select
            value={currentConversation?.database || ''}
            onValueChange={setDatabase}
            disabled={isLoadingDatabases}
          >
            <SelectTrigger className="w-48 h-8 text-sm">
              <SelectValue placeholder={
                isLoadingDatabases ? "Loading..." : "Select database"
              } />
            </SelectTrigger>
            <SelectContent>
              {availableDatabases.length === 0 && !isLoadingDatabases && (
                <SelectItem value="" disabled>
                  No databases available
                </SelectItem>
              )}
              {availableDatabases.map((db) => (
                <SelectItem key={db.name} value={db.name}>
                  {db.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-xs text-gray-500">
            {currentConversation?.messages.length || 0} messages
          </span>
        </div>

        {/* Input Area */}
        <div className="flex items-end space-x-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything about your data..."
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={1}
              style={{ maxHeight: '200px' }}
              disabled={isLoading}
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="h-12 px-6 bg-blue-600 hover:bg-blue-700"
          >
            {isLoading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
            ) : (
              <>
                <Send size={18} className="mr-2" />
                Send
              </>
            )}
          </Button>
        </div>

        <p className="text-xs text-gray-500 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
