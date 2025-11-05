'use client';

import { useState } from 'react';
import { Lightbulb, AlertTriangle, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface AnalysisSummaryProps {
  insights?: string[];
  recommendations?: string[];
  warnings?: string[];
  errors?: string[];
}

export default function AnalysisSummary({
  insights,
  recommendations,
  warnings,
  errors
}: AnalysisSummaryProps) {
  const [showWarnings, setShowWarnings] = useState(false);

  // Don't render if no content
  if (!insights?.length && !recommendations?.length && !warnings?.length && !errors?.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      {/* Header */}
      <div className="flex items-center mb-3">
        <Lightbulb size={18} className="text-blue-600 mr-2" />
        <h4 className="text-base font-semibold text-gray-900">
          Analysis Summary
        </h4>
      </div>

      <div className="space-y-4 text-sm text-gray-700">
        {/* Insights */}
        {insights && insights.length > 0 && (
          <div>
            <h5 className="font-medium text-gray-900 mb-2">Key Insights:</h5>
            <ul className="space-y-1.5 ml-5">
              {insights.map((insight, idx) => (
                <li key={idx} className="list-disc">
                  {insight}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {recommendations && recommendations.length > 0 && (
          <div>
            <h5 className="font-medium text-gray-900 mb-2">Recommendations:</h5>
            <ul className="space-y-1.5 ml-5">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="list-disc text-blue-700">
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Warnings (Collapsible) */}
        {warnings && warnings.length > 0 && (
          <div>
            <Button
              variant="ghost"
              size="sm"
              className="text-orange-700 hover:text-orange-900 px-0 mb-2"
              onClick={() => setShowWarnings(!showWarnings)}
            >
              <AlertTriangle size={16} className="mr-2" />
              <span className="font-medium">
                {showWarnings ? 'Hide' : 'Show'} warnings ({warnings.length})
              </span>
              <ChevronDown
                size={16}
                className={`ml-1 transition-transform ${showWarnings ? 'rotate-180' : ''}`}
              />
            </Button>

            {showWarnings && (
              <ul className="space-y-1.5 ml-5">
                {warnings.map((warning, idx) => (
                  <li key={idx} className="list-disc text-orange-700">
                    {warning}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Errors (Always Visible) */}
        {errors && errors.length > 0 && (
          <div>
            <h5 className="font-medium text-red-900 mb-2">Errors:</h5>
            <ul className="space-y-1.5 ml-5">
              {errors.map((error, idx) => (
                <li key={idx} className="list-disc text-red-700">
                  {error}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
