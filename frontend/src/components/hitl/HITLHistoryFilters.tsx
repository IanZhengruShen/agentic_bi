/**
 * HITLHistoryFilters Component
 *
 * Filter controls for HITL history view.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { HITLHistoryFilters as Filters } from '@/types/hitl.types';
import { Filter, X } from 'lucide-react';

interface HITLHistoryFiltersProps {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
}

export function HITLHistoryFilters({ filters, onFiltersChange }: HITLHistoryFiltersProps) {
  const [localFilters, setLocalFilters] = useState<Filters>(filters);

  /**
   * Apply filters
   */
  const handleApply = () => {
    onFiltersChange(localFilters);
  };

  /**
   * Clear all filters
   */
  const handleClear = () => {
    const emptyFilters: Filters = {};
    setLocalFilters(emptyFilters);
    onFiltersChange(emptyFilters);
  };

  /**
   * Update single filter
   */
  const updateFilter = (key: keyof Filters, value: any) => {
    setLocalFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
    }));
  };

  return (
    <div className="space-y-4 bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-gray-600" />
        <h3 className="font-semibold text-sm text-gray-700">Filters</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Intervention Type */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-700">Intervention Type</label>
          <Select
            value={localFilters.intervention_type || 'all'}
            onValueChange={(value) =>
              updateFilter('intervention_type', value === 'all' ? undefined : value)
            }
          >
            <SelectTrigger className="h-9">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="sql_review">SQL Review</SelectItem>
              <SelectItem value="data_modification">Data Modification</SelectItem>
              <SelectItem value="high_cost_query">High Cost Query</SelectItem>
              <SelectItem value="schema_change">Schema Change</SelectItem>
              <SelectItem value="export_approval">Export Approval</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Status */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-700">Status</label>
          <Select
            value={localFilters.status || 'all'}
            onValueChange={(value) =>
              updateFilter('status', value === 'all' ? undefined : value)
            }
          >
            <SelectTrigger className="h-9">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
              <SelectItem value="modified">Modified</SelectItem>
              <SelectItem value="timeout">Timeout</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Date From */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-700">From Date</label>
          <Input
            type="date"
            value={localFilters.date_from || ''}
            onChange={(e) => updateFilter('date_from', e.target.value)}
            className="h-9"
          />
        </div>

        {/* Date To */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-700">To Date</label>
          <Input
            type="date"
            value={localFilters.date_to || ''}
            onChange={(e) => updateFilter('date_to', e.target.value)}
            className="h-9"
          />
        </div>
      </div>

      {/* Search */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-gray-700">Search</label>
        <Input
          type="text"
          placeholder="Search by query, SQL, or feedback..."
          value={localFilters.search || ''}
          onChange={(e) => updateFilter('search', e.target.value)}
          className="h-9"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button onClick={handleApply} size="sm" className="flex-1">
          <Filter className="h-4 w-4 mr-2" />
          Apply Filters
        </Button>
        <Button onClick={handleClear} variant="outline" size="sm">
          <X className="h-4 w-4 mr-2" />
          Clear
        </Button>
      </div>
    </div>
  );
}
