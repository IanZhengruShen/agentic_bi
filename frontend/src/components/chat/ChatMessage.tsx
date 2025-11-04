'use client';

import { Message } from '@/stores/conversation.store';
import { User, Bot } from 'lucide-react';
import MessageContent from './MessageContent';

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
        </div>
      )}

      <div className={`flex-1 max-w-3xl ${isUser ? 'flex justify-end' : ''}`}>
        {isUser ? (
          <div className="bg-blue-600 text-white px-4 py-3 rounded-lg max-w-lg">
            <p className="text-sm">{message.content}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {message.isLoading ? (
              <div className="space-y-3">
                <div className="flex items-center space-x-2 text-gray-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                  <span className="text-sm font-medium">
                    {message.progress?.message || 'Thinking...'}
                  </span>
                </div>

                {/* Progress bar */}
                {message.progress && (
                  <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-purple-500 h-1.5 rounded-full transition-all duration-500 ease-out"
                      style={{ width: getProgressWidth(message.progress.stage) }}
                    ></div>
                  </div>
                )}
              </div>
            ) : (
              <>
                <p className="text-gray-900">{message.content}</p>
                {message.workflowResponse && (
                  <MessageContent response={message.workflowResponse} />
                )}
              </>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
            <User size={18} className="text-gray-600" />
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Calculate progress bar width based on workflow stage
 */
function getProgressWidth(stage: string): string {
  switch (stage) {
    case 'starting':
      return '10%';
    case 'started':
      return '15%';
    case 'analysis':
      return '35%';
    case 'deciding':
      return '55%';
    case 'visualizing':
      return '75%';
    case 'finalizing':
      return '90%';
    case 'agent':
      return '50%';
    case 'failed':
      return '100%';
    default:
      return '25%';
  }
}
