/**
 * HITL (Human-in-the-Loop) Type Definitions
 *
 * Types for frontend HITL system matching backend models.
 */

/**
 * Intervention types supported by the system
 */
export type HITLInterventionType =
  | 'sql_review'
  | 'data_modification'
  | 'high_cost_query'
  | 'schema_change'
  | 'export_approval'
  | 'custom';

/**
 * Request status values
 */
export type HITLRequestStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'modified'
  | 'timeout'
  | 'cancelled';

/**
 * Context data structure (flexible based on intervention type)
 */
export interface HITLContext {
  // SQL Review fields
  generated_sql?: string;
  confidence?: number;
  user_query?: string;
  affected_tables?: string[];

  // Data Modification fields
  operation?: string;
  affected_rows_estimate?: number;

  // High Cost Query fields
  estimated_cost?: number;
  estimated_rows?: number;

  // Allow additional fields
  [key: string]: any;
}

/**
 * Action option presented to user
 */
export interface HITLOption {
  action: string; // approve, reject, modify, abort
  label: string;
  description?: string;
  icon?: string;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary';
}

/**
 * HITL request received from backend via WebSocket or API
 */
export interface HITLRequest {
  request_id: string;
  workflow_id: string;
  conversation_id?: string;
  intervention_type: HITLInterventionType;
  context: HITLContext;
  options: HITLOption[];
  timeout_seconds: number;
  timeout_at: string; // ISO timestamp
  requested_at: string; // ISO timestamp
  status: HITLRequestStatus;
  required: boolean;
}

/**
 * Payload sent to backend when responding to HITL request
 */
export interface HITLResponsePayload {
  request_id: string;
  action: string;
  data?: Record<string, any>;
  feedback?: string;
  modified_sql?: string;
}

/**
 * Response from backend after submitting HITL response
 */
export interface HITLResponseResult {
  success: boolean;
  message: string;
  request_id: string;
}

/**
 * HITL history item (past intervention)
 */
export interface HITLHistoryItem {
  id: string;
  request_id: string;
  workflow_id: string;
  conversation_id?: string;
  intervention_type: HITLInterventionType;
  status: HITLRequestStatus;
  requested_at: string;
  responded_at?: string;
  response_time_ms?: number;
  action?: string;
  responder_name?: string;
  responder_email?: string;
  context: HITLContext;
  feedback?: string;
}

/**
 * Filters for history query
 */
export interface HITLHistoryFilters {
  intervention_type?: HITLInterventionType;
  status?: HITLRequestStatus;
  date_from?: string; // ISO date string
  date_to?: string; // ISO date string
  search?: string;
}

/**
 * User notification preferences
 */
export interface NotificationPreferences {
  websocket_enabled: boolean;
  email_enabled: boolean;
  slack_enabled: boolean;
  slack_channel?: string;
  intervention_types: HITLInterventionType[];
}

/**
 * Pending requests response from backend
 */
export interface PendingRequestsResponse {
  workflow_id: string;
  count: number;
  requests: HITLRequest[];
}
