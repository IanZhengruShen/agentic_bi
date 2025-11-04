/**
 * HITLDebugPanel Component
 *
 * Debug panel to visualize HITL state (dev mode only).
 * Shows pending request, time remaining, and WebSocket subscription status.
 */

'use client';

import { useHITLStore } from '@/stores/hitl.store';
import { useConversationStore } from '@/stores/conversation.store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Bug, Clock, Wifi } from 'lucide-react';

export function HITLDebugPanel() {
  const { pendingRequest, timeRemaining } = useHITLStore();
  const { currentConversation } = useConversationStore();

  // Only show in development
  if (process.env.NODE_ENV === 'production') return null;

  return (
    <Card className="fixed bottom-4 right-4 w-80 shadow-lg border-2 border-purple-500 z-50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Bug className="h-4 w-4 text-purple-600" />
          HITL Debug Panel
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {/* Workflow ID */}
        <div>
          <span className="font-semibold">Workflow ID:</span>
          <p className="font-mono text-[10px] bg-gray-100 p-1 rounded mt-1 break-all">
            {currentConversation?.currentWorkflowId || 'None'}
          </p>
        </div>

        {/* Conversation ID */}
        <div>
          <span className="font-semibold">Conversation ID:</span>
          <p className="font-mono text-[10px] bg-gray-100 p-1 rounded mt-1 break-all">
            {currentConversation?.id || 'None'}
          </p>
        </div>

        {/* Pending Request */}
        <div>
          <span className="font-semibold">Pending Request:</span>
          {pendingRequest ? (
            <div className="mt-1 space-y-1">
              <Badge variant="destructive" className="text-xs">
                {pendingRequest.intervention_type}
              </Badge>
              <p className="font-mono text-[10px] bg-red-50 p-1 rounded break-all">
                {pendingRequest.request_id}
              </p>
            </div>
          ) : (
            <p className="text-gray-500 italic mt-1">None</p>
          )}
        </div>

        {/* Time Remaining */}
        <div className="flex items-center gap-2">
          <Clock className="h-3 w-3" />
          <span className="font-semibold">Time Remaining:</span>
          <Badge variant={timeRemaining > 0 ? 'default' : 'outline'}>
            {timeRemaining}s
          </Badge>
        </div>

        {/* WebSocket Status */}
        <div className="pt-2 border-t">
          <p className="text-[10px] text-gray-500">
            Check browser console for WebSocket logs
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
