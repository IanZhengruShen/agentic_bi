'use client';

import { WorkflowResponse } from '@/types/workflow.types';
import PlotlyChart from './PlotlyChart';
import DataTable from './DataTable';
import SQLQuery from './SQLQuery';
import AnalysisSummary from './AnalysisSummary';
import { chartService } from '@/services/chart.service';
import { useConversationStore } from '@/stores/conversation.store';

interface MessageContentProps {
  response: WorkflowResponse;
  messageId?: string; // For tracking
}

export default function MessageContent({ response, messageId }: MessageContentProps) {
  const { analysis, visualization, insights, recommendations, warnings, errors } = response;
  const { defaultChartConfig } = useConversationStore();

  // Generate unique chart ID
  const chartId = messageId ? `${messageId}_chart` : chartService.generateChartId();

  return (
    <div className="space-y-3">

      {/* 1. Chart (highest priority) - auto-applies user preferences */}
      {visualization?.plotly_figure && (
        <PlotlyChart
          figure={visualization.plotly_figure}
          title={visualization.chart_type}
          chartId={chartId}
          config={defaultChartConfig} // Auto-apply user preferences
        />
      )}

      {/* 2. Data Table */}
      {analysis?.data && analysis.data.length > 0 && (
        <DataTable
          data={analysis.data}
          rowCount={analysis.row_count || analysis.data.length}
          maxRows={5}
        />
      )}

      {/* 3. SQL Query (collapsed by default) */}
      {analysis?.generated_sql && (
        <SQLQuery
          sql={analysis.generated_sql}
          confidence={analysis.sql_confidence ?? undefined}
          defaultExpanded={false}
        />
      )}

      {/* 4. Analysis Summary (ALL TEXT CONTENT) */}
      <AnalysisSummary
        insights={insights}
        recommendations={recommendations}
        warnings={warnings}
        errors={errors}
      />

    </div>
  );
}
