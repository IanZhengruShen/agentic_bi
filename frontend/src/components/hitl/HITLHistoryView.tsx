/**
 * HITLHistoryView Component
 *
 * Main view for displaying HITL intervention history.
 */

'use client';

import { useEffect } from 'react';
import { useHITLStore } from '@/stores/hitl.store';
import { HITLRequestCard } from './HITLRequestCard';
import { HITLHistoryFilters } from './HITLHistoryFilters';
import { Button } from '@/components/ui/button';
import { Download, History, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export function HITLHistoryView() {
  const {
    history,
    historyFilters,
    isLoadingHistory,
    fetchHistory,
    setHistoryFilters,
  } = useHITLStore();

  // Fetch history on mount
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  /**
   * Export history to CSV
   */
  const handleExportCSV = () => {
    if (history.length === 0) {
      toast.error('No data to export');
      return;
    }

    try {
      // Prepare CSV data
      const headers = [
        'Request ID',
        'Type',
        'Status',
        'Requested At',
        'Responded At',
        'Response Time (ms)',
        'Action',
        'Responder',
        'Feedback',
      ];

      const rows = history.map((item) => [
        item.request_id,
        item.intervention_type,
        item.status,
        item.requested_at,
        item.responded_at || '',
        item.response_time_ms?.toString() || '',
        item.action || '',
        item.responder_name || '',
        item.feedback || '',
      ]);

      const csvContent = [
        headers.join(','),
        ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
      ].join('\n');

      // Create download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      link.setAttribute('href', url);
      link.setAttribute('download', `hitl-history-${Date.now()}.csv`);
      link.style.visibility = 'hidden';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success('History exported', {
        description: `${history.length} items exported to CSV`,
      });
    } catch (error) {
      console.error('Export failed:', error);
      toast.error('Failed to export history');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Intervention History</h1>
        </div>
        <Button onClick={handleExportCSV} variant="outline" disabled={history.length === 0}>
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <HITLHistoryFilters filters={historyFilters} onFiltersChange={setHistoryFilters} />

      {/* Loading State */}
      {isLoadingHistory && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      )}

      {/* Empty State */}
      {!isLoadingHistory && history.length === 0 && (
        <div className="text-center py-12 bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg">
          <History className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No interventions found</h3>
          <p className="text-sm text-gray-600">
            {Object.keys(historyFilters).length > 0
              ? 'Try adjusting your filters'
              : 'Interventions will appear here once you start using HITL features'}
          </p>
        </div>
      )}

      {/* History List */}
      {!isLoadingHistory && history.length > 0 && (
        <div className="space-y-4">
          <div className="text-sm text-gray-600">
            Showing <span className="font-semibold">{history.length}</span> intervention
            {history.length !== 1 ? 's' : ''}
          </div>

          <div className="space-y-3">
            {history.map((item) => (
              <HITLRequestCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
