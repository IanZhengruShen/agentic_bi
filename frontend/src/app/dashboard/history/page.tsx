/**
 * History Page
 *
 * Displays HITL intervention history with filters and export.
 */

'use client';

import { HITLHistoryView } from '@/components/hitl/HITLHistoryView';

export default function HistoryPage() {
  return (
    <div className="container mx-auto py-8 px-6">
      <HITLHistoryView />
    </div>
  );
}
