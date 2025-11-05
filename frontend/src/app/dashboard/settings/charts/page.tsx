'use client';

/**
 * Chart Settings Page - Redirect to main Settings
 *
 * This page now redirects to /dashboard/settings with the charts tab active
 * to maintain backward compatibility with bookmarks and old links.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ChartSettingsRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to main settings page with charts tab
    router.replace('/dashboard/settings?tab=charts');
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
        <p className="text-gray-600">Redirecting to Settings...</p>
      </div>
    </div>
  );
}
