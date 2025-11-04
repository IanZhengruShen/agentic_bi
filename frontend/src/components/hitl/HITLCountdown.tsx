/**
 * HITLCountdown Component
 *
 * Displays countdown timer for HITL request timeout.
 */

import { Clock } from 'lucide-react';

interface HITLCountdownProps {
  timeRemaining: number; // seconds
}

export function HITLCountdown({ timeRemaining }: HITLCountdownProps) {
  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;

  // Determine color based on time remaining
  const getColorClass = () => {
    if (timeRemaining <= 30) return 'text-red-600';
    if (timeRemaining <= 60) return 'text-orange-600';
    return 'text-gray-600';
  };

  return (
    <div className={`flex items-center gap-2 text-sm font-medium ${getColorClass()}`}>
      <Clock className="h-4 w-4" />
      <span>
        {minutes}:{String(seconds).padStart(2, '0')} remaining
      </span>
    </div>
  );
}
