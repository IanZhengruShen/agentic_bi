/**
 * HITLApprovalModal Component
 *
 * Main modal for displaying HITL requests and collecting user responses.
 * Shows intervention details, context, and action buttons.
 */

'use client';

import { useState } from 'react';
import { useHITLStore } from '@/stores/hitl.store';
import { HITLCountdown } from './HITLCountdown';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle2, XCircle, Edit3 } from 'lucide-react';
import { toast } from 'sonner';

export function HITLApprovalModal() {
  const { pendingRequest, timeRemaining, submitResponse, isSubmitting, error } = useHITLStore();
  const [feedback, setFeedback] = useState('');
  const [modifiedSql, setModifiedSql] = useState('');
  const [showSqlEditor, setShowSqlEditor] = useState(false);

  if (!pendingRequest) return null;

  const { request_id, intervention_type, context, options } = pendingRequest;

  /**
   * Handle action button click
   */
  const handleAction = async (action: string) => {
    try {
      await submitResponse({
        request_id,
        action,
        feedback: feedback || undefined,
        modified_sql: action === 'modify' ? modifiedSql : undefined,
      });

      toast.success('Response submitted', {
        description: `Action: ${action}`,
      });

      // Reset state
      setFeedback('');
      setModifiedSql('');
      setShowSqlEditor(false);
    } catch (err) {
      toast.error('Failed to submit response', {
        description: error || 'An error occurred',
      });
    }
  };

  /**
   * Get icon for intervention type
   */
  const getInterventionIcon = () => {
    switch (intervention_type) {
      case 'sql_review':
        return <AlertCircle className="h-5 w-5" />;
      case 'data_modification':
        return <Edit3 className="h-5 w-5" />;
      default:
        return <AlertCircle className="h-5 w-5" />;
    }
  };

  /**
   * Get variant for action button
   */
  const getButtonVariant = (option: typeof options[0]) => {
    if (option.variant) return option.variant;
    if (option.action === 'approve') return 'default';
    if (option.action === 'reject') return 'destructive';
    return 'outline';
  };

  /**
   * Get icon for action button
   */
  const getActionIcon = (action: string) => {
    switch (action) {
      case 'approve':
        return <CheckCircle2 className="h-4 w-4 mr-2" />;
      case 'reject':
        return <XCircle className="h-4 w-4 mr-2" />;
      case 'modify':
        return <Edit3 className="h-4 w-4 mr-2" />;
      default:
        return null;
    }
  };

  return (
    <Dialog open={true}>
      <DialogContent className="max-w-lg max-h-[60vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-lg">
              {getInterventionIcon()}
              Human Review Required
            </DialogTitle>
            <HITLCountdown timeRemaining={timeRemaining} />
          </div>
          <DialogDescription className="text-sm">
            Please review and take action.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Intervention Type Badge */}
          <div>
            <Badge variant="outline" className="text-xs">
              {intervention_type.replace('_', ' ').toUpperCase()}
            </Badge>
          </div>

          {/* SQL Review Context */}
          {intervention_type === 'sql_review' && context.generated_sql && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-sm text-gray-700">Generated SQL</h4>
                {context.confidence !== undefined && (
                  <Badge
                    variant={context.confidence >= 0.9 ? 'default' : 'secondary'}
                    className="text-xs"
                  >
                    Confidence: {(context.confidence * 100).toFixed(0)}%
                  </Badge>
                )}
              </div>

              {!showSqlEditor ? (
                <pre className="bg-gray-50 border border-gray-200 rounded-md p-3 text-xs overflow-x-auto max-h-[120px]">
                  <code>{context.generated_sql}</code>
                </pre>
              ) : (
                <Textarea
                  value={modifiedSql || context.generated_sql}
                  onChange={(e) => setModifiedSql(e.target.value)}
                  className="font-mono text-xs min-h-[100px] max-h-[150px]"
                  placeholder="Edit SQL..."
                />
              )}

              {context.user_query && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Original Query:</span> {context.user_query}
                </div>
              )}

              {context.affected_tables && context.affected_tables.length > 0 && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Affected Tables:</span>{' '}
                  {context.affected_tables.join(', ')}
                </div>
              )}
            </div>
          )}

          {/* Data Modification Context */}
          {intervention_type === 'data_modification' && (
            <div className="space-y-3 bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-orange-700">
                <AlertCircle className="h-5 w-5" />
                <h4 className="font-semibold">Data Modification Warning</h4>
              </div>
              {context.operation && (
                <p className="text-sm text-orange-600">
                  Operation: <span className="font-mono font-semibold">{context.operation}</span>
                </p>
              )}
              {context.affected_rows_estimate && (
                <p className="text-sm text-orange-600">
                  Estimated Affected Rows: {context.affected_rows_estimate.toLocaleString()}
                </p>
              )}
              {context.generated_sql && (
                <pre className="bg-white border border-orange-200 rounded p-3 text-sm overflow-x-auto">
                  <code>{context.generated_sql}</code>
                </pre>
              )}
            </div>
          )}

          {/* High Cost Query Context */}
          {intervention_type === 'high_cost_query' && (
            <div className="space-y-3 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-yellow-700">
                <AlertCircle className="h-5 w-5" />
                <h4 className="font-semibold">High Cost Query Warning</h4>
              </div>
              {context.estimated_cost && (
                <p className="text-sm text-yellow-600">
                  Estimated Cost: {context.estimated_cost.toLocaleString()}
                </p>
              )}
              {context.estimated_rows && (
                <p className="text-sm text-yellow-600">
                  Estimated Rows: {context.estimated_rows.toLocaleString()}
                </p>
              )}
            </div>
          )}

          {/* Feedback Textarea */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-700">
              Feedback (Optional)
            </label>
            <Textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Add any comments or notes..."
              className="min-h-[50px] max-h-[80px] text-sm"
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            {options.map((option) => (
              <Button
                key={option.action}
                onClick={() => {
                  if (option.action === 'modify' && !showSqlEditor) {
                    setShowSqlEditor(true);
                    setModifiedSql(context.generated_sql || '');
                  } else {
                    handleAction(option.action);
                  }
                }}
                variant={getButtonVariant(option)}
                disabled={isSubmitting}
                className="flex-1"
              >
                {getActionIcon(option.action)}
                {option.label}
              </Button>
            ))}
          </div>

          {showSqlEditor && (
            <p className="text-xs text-gray-500 text-center">
              Edit the SQL above, then click &quot;Modify SQL&quot; again to submit.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
