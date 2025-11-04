/**
 * Notification Settings Page
 *
 * Configure user notification preferences for HITL interventions.
 */

'use client';

import { HITLPreferences } from '@/components/hitl/HITLPreferences';

export default function NotificationSettingsPage() {
  return (
    <div className="container mx-auto py-8 px-6">
      <HITLPreferences />
    </div>
  );
}
