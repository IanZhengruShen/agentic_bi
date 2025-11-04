/**
 * HITLRequestCard Component
 *
 * Displays a single HITL request in the history view.
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { HITLHistoryItem } from '@/types/hitl.types';
import { CheckCircle2, XCircle, Clock, Edit3, Ban } from 'lucide-react';
import { format } from 'date-fns';

interface HITLRequestCardProps {
  item: HITLHistoryItem;
}

export function HITLRequestCard({ item }: HITLRequestCardProps) {
  /**
   * Get badge variant for status
   */
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'approved':
        return 'default';
      case 'rejected':
        return 'destructive';
      case 'modified':
        return 'secondary';
      case 'timeout':
        return 'outline';
      case 'cancelled':
        return 'outline';
      default:
        return 'outline';
    }
  };

  /**
   * Get icon for status
   */
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'rejected':
        return <XCircle className="h-4 w-4" />;
      case 'modified':
        return <Edit3 className="h-4 w-4" />;
      case 'timeout':
        return <Clock className="h-4 w-4" />;
      case 'cancelled':
        return <Ban className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  /**
   * Format response time
   */
  const formatResponseTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {item.intervention_type.replace('_', ' ').toUpperCase()}
            </Badge>
            <Badge variant={getStatusVariant(item.status)} className="text-xs flex items-center gap-1">
              {getStatusIcon(item.status)}
              {item.status.toUpperCase()}
            </Badge>
          </div>
          <span className="text-xs text-gray-500">
            {format(new Date(item.requested_at), 'MMM d, yyyy HH:mm')}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-2">
        {/* Context Information */}
        {item.context.user_query && (
          <div className="text-sm">
            <span className="font-medium text-gray-700">Query:</span>{' '}
            <span className="text-gray-600">{item.context.user_query}</span>
          </div>
        )}

        {item.context.generated_sql && (
          <div className="text-sm">
            <span className="font-medium text-gray-700">SQL:</span>
            <pre className="mt-1 bg-gray-50 border border-gray-200 rounded p-2 text-xs overflow-x-auto">
              <code>{item.context.generated_sql.substring(0, 150)}
                {item.context.generated_sql.length > 150 && '...'}
              </code>
            </pre>
          </div>
        )}

        {/* Response Information */}
        <div className="flex flex-wrap gap-4 text-xs text-gray-500 pt-2 border-t">
          {item.responded_at && (
            <div>
              <span className="font-medium">Responded:</span>{' '}
              {format(new Date(item.responded_at), 'HH:mm:ss')}
            </div>
          )}

          {item.response_time_ms !== undefined && (
            <div>
              <span className="font-medium">Response Time:</span>{' '}
              {formatResponseTime(item.response_time_ms)}
            </div>
          )}

          {item.responder_name && (
            <div>
              <span className="font-medium">By:</span> {item.responder_name}
            </div>
          )}

          {item.action && (
            <div>
              <span className="font-medium">Action:</span> {item.action}
            </div>
          )}
        </div>

        {/* Feedback */}
        {item.feedback && (
          <div className="text-sm bg-blue-50 border border-blue-200 rounded p-2 mt-2">
            <span className="font-medium text-blue-700">Feedback:</span>{' '}
            <span className="text-blue-600">{item.feedback}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
