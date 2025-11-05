'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Download, Copy, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import Papa from 'papaparse';

interface DataTableProps {
  data: Record<string, any>[];
  rowCount?: number; // Total row count from backend (may be more than data.length)
  maxRows?: number; // Max rows to show per page (default: 5)
}

export default function DataTable({ data, rowCount, maxRows = 5 }: DataTableProps) {
  const [currentPage, setCurrentPage] = useState(1);

  if (!data || data.length === 0) {
    return null;
  }

  // Get column names from first row
  const columns = Object.keys(data[0]);

  // Calculate pagination
  const totalRows = rowCount || data.length;
  const displayData = data.slice(0, maxRows); // Show only first maxRows
  const totalPages = Math.ceil(totalRows / maxRows);
  const paginatedData = displayData.slice(
    (currentPage - 1) * maxRows,
    currentPage * maxRows
  );

  // Export to CSV
  const handleExportCSV = () => {
    try {
      const csv = Papa.unparse(data);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `data_export_${Date.now()}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success('CSV exported successfully');
    } catch (error) {
      toast.error('Failed to export CSV');
      console.error('Export error:', error);
    }
  };

  // Copy to clipboard
  const handleCopy = () => {
    try {
      const csv = Papa.unparse(data);
      navigator.clipboard.writeText(csv);
      toast.success('Data copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy data');
      console.error('Copy error:', error);
    }
  };

  // Format cell values
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      return value.toLocaleString();
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    return String(value);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Header with actions */}
      <div className="flex justify-between items-center px-4 py-3 border-b border-gray-200">
        <div className="text-sm text-gray-600">
          Showing {displayData.length} of {totalRows.toLocaleString()} rows
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={handleCopy}
            title="Copy to clipboard"
          >
            <Copy size={14} className="mr-1" />
            Copy
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleExportCSV}
            title="Export as CSV"
          >
            <Download size={14} className="mr-1" />
            CSV
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left font-medium text-gray-700"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
              >
                {columns.map((col) => (
                  <td
                    key={`${rowIdx}-${col}`}
                    className="px-4 py-2 text-gray-900 border-b border-gray-100"
                  >
                    {formatValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination (only show if more than maxRows) */}
      {totalRows > maxRows && (
        <div className="flex justify-between items-center px-4 py-3 border-t border-gray-200">
          <div className="text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
            >
              <ChevronLeft size={14} className="mr-1" />
              Previous
            </Button>

            {/* Page numbers */}
            <div className="flex gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }

                return (
                  <Button
                    key={pageNum}
                    size="sm"
                    variant={currentPage === pageNum ? 'default' : 'ghost'}
                    onClick={() => setCurrentPage(pageNum)}
                    className="w-8 h-8 p-0"
                  >
                    {pageNum}
                  </Button>
                );
              })}
            </div>

            <Button
              size="sm"
              variant="ghost"
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
            >
              Next
              <ChevronRight size={14} className="ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
