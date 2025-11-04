/**
 * Workflow type definitions.
 *
 * Matches backend UnifiedWorkflow schemas.
 */

export interface WorkflowOptions {
  auto_visualize?: boolean;
  chart_type?: 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'table' | null;
  plotly_theme?: string;
  custom_style_profile_id?: string | null;
  include_insights?: boolean;
  limit_rows?: number;
  timeout_seconds?: number;
}

export interface WorkflowRequest {
  query: string;
  database: string;
  workflow_id?: string;
  conversation_id?: string;
  options?: WorkflowOptions;
}

export interface AnalysisResults {
  session_id: string;
  generated_sql: string | null;
  sql_confidence: number | null;
  row_count: number;
  data: Array<Record<string, any>>;
  analysis_summary: any;
  enhanced_analysis: any;
}

export interface VisualizationResults {
  visualization_id: string;
  chart_type: string;
  plotly_figure: any;
  chart_recommendation_reasoning: string | null;
  recommendation_confidence: number | null;
  insights: string[];
}

export interface WorkflowMetadata {
  workflow_id: string;
  conversation_id: string;
  workflow_status: 'completed' | 'partial_success' | 'failed';
  workflow_stage: string | null;
  agents_executed: string[];
  execution_time_ms: number;
  created_at: string;
  completed_at: string;
}

export interface WorkflowResponse {
  metadata: WorkflowMetadata;
  analysis: AnalysisResults | null;
  visualization: VisualizationResults | null;
  insights: string[];
  recommendations: string[];
  errors: string[];
  warnings: string[];
  should_visualize: boolean;
  visualization_reasoning: string | null;
}
