'use client';

import { WorkflowResponse } from '@/types/workflow.types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  Code,
  Lightbulb,
  AlertTriangle,
  Sparkles,
  Copy,
  Download
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import PlotlyChart from './PlotlyChart';

interface MessageContentProps {
  response: WorkflowResponse;
}

export default function MessageContent({ response }: MessageContentProps) {
  const { analysis, visualization, insights, recommendations, warnings, errors } = response;

  return (
    <div className="space-y-4">
      {/* Visualization Chart */}
      {visualization && visualization.plotly_figure && (
        <PlotlyChart
          figure={visualization.plotly_figure}
          title={visualization.chart_type ? `${visualization.chart_type.charAt(0).toUpperCase() + visualization.chart_type.slice(1)} Chart` : undefined}
        />
      )}
      {/* Data Table */}
      {analysis && analysis.data && analysis.data.length > 0 && (
        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex justify-between items-center">
              <CardTitle className="text-base flex items-center">
                <Table size={18} className="mr-2" />
                Results ({analysis.row_count} rows)
              </CardTitle>
              <div className="flex space-x-2">
                <Button size="sm" variant="ghost">
                  <Copy size={14} className="mr-1" /> Copy
                </Button>
                <Button size="sm" variant="ghost">
                  <Download size={14} className="mr-1" /> Export
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <DataTableView data={analysis.data.slice(0, 10)} />
            {analysis.row_count > 10 && (
              <p className="text-xs text-gray-500 mt-2">
                Showing first 10 of {analysis.row_count} rows
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* SQL Query */}
      {analysis && analysis.generated_sql && (
        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex justify-between items-center">
              <CardTitle className="text-base flex items-center">
                <Code size={18} className="mr-2" />
                Generated SQL
              </CardTitle>
              <div className="flex items-center space-x-2">
                {analysis.sql_confidence && (
                  <Badge variant="outline">
                    {Math.round(analysis.sql_confidence * 100)}% confidence
                  </Badge>
                )}
                <Button size="sm" variant="ghost">
                  <Copy size={14} />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-x-auto">
              {analysis.generated_sql}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Insights */}
      {insights && insights.length > 0 && (
        <div className="space-y-2">
          {insights.map((insight, idx) => (
            <div
              key={idx}
              className="flex items-start space-x-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg"
            >
              <Sparkles size={16} className="text-yellow-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-yellow-900">{insight}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div className="space-y-2">
          {recommendations.map((rec, idx) => (
            <div
              key={idx}
              className="flex items-start space-x-2 p-3 bg-blue-50 border border-blue-200 rounded-lg"
            >
              <Lightbulb size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-blue-900">{rec}</p>
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="space-y-2">
          {warnings.map((warning, idx) => (
            <div
              key={idx}
              className="flex items-start space-x-2 p-3 bg-orange-50 border border-orange-200 rounded-lg"
            >
              <AlertTriangle size={16} className="text-orange-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-orange-900">{warning}</p>
            </div>
          ))}
        </div>
      )}

      {/* Errors */}
      {errors && errors.length > 0 && (
        <div className="space-y-2">
          {errors.map((error, idx) => (
            <div
              key={idx}
              className="flex items-start space-x-2 p-3 bg-red-50 border border-red-200 rounded-lg"
            >
              <AlertTriangle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-900">{error}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Simple data table component
function DataTableView({ data }: { data: Array<Record<string, any>> }) {
  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left text-xs font-medium text-gray-700"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx} className="border-b hover:bg-gray-50">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-xs">
                  {formatCellValue(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCellValue(value: any): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}
