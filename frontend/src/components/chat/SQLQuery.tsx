'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Code, Copy, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';

interface SQLQueryProps {
  sql: string;
  confidence?: number; // SQL generation confidence (0-1)
  defaultExpanded?: boolean; // Whether to show expanded by default
}

export default function SQLQuery({
  sql,
  confidence,
  defaultExpanded = false
}: SQLQueryProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!sql) {
    return null;
  }

  const handleCopy = () => {
    try {
      navigator.clipboard.writeText(sql);
      toast.success('SQL copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy SQL');
      console.error('Copy error:', error);
    }
  };

  // Get confidence badge color
  const getConfidenceBadge = () => {
    if (!confidence) return null;

    const percentage = Math.round(confidence * 100);
    let variant: 'default' | 'secondary' | 'destructive' | 'outline' = 'secondary';
    let color = 'text-gray-600';

    if (percentage >= 90) {
      variant = 'default';
      color = 'text-green-600';
    } else if (percentage >= 70) {
      variant = 'secondary';
      color = 'text-blue-600';
    } else {
      variant = 'outline';
      color = 'text-orange-600';
    }

    return (
      <Badge variant={variant} className={color}>
        {percentage}% confidence
      </Badge>
    );
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Header (Clickable to expand/collapse) */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex justify-between items-center px-4 py-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Code size={18} className="text-gray-600" />
          <span className="text-sm font-medium text-gray-900">
            SQL Query
          </span>
          {getConfidenceBadge()}
        </div>
        <ChevronDown
          size={16}
          className={`text-gray-600 transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* SQL Content (Collapsible) */}
      {isExpanded && (
        <div className="border-t border-gray-200">
          <div className="px-4 py-3">
            {/* SQL Code Block */}
            <div className="relative">
              <pre className="bg-gray-900 text-gray-100 rounded-md p-4 overflow-x-auto text-sm">
                <code>{sql}</code>
              </pre>

              {/* Copy button (positioned in top-right of code block) */}
              <Button
                size="sm"
                variant="ghost"
                onClick={handleCopy}
                className="absolute top-2 right-2 bg-gray-800 hover:bg-gray-700 text-gray-300"
                title="Copy SQL"
              >
                <Copy size={14} className="mr-1" />
                Copy
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
