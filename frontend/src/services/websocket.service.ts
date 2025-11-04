/**
 * WebSocket Service for Real-time Workflow Updates
 *
 * Manages WebSocket connections to the backend for receiving real-time
 * workflow progress events. Uses JWT authentication and supports automatic
 * reconnection.
 *
 * @module websocket.service
 */

/**
 * Workflow event types from backend
 */
export enum WorkflowEventType {
  // Workflow events
  WORKFLOW_STARTED = 'workflow.started',
  WORKFLOW_COMPLETED = 'workflow.completed',
  WORKFLOW_FAILED = 'workflow.failed',
  WORKFLOW_PAUSED = 'workflow.paused',
  WORKFLOW_RESUMED = 'workflow.resumed',

  // Stage events
  STAGE_STARTED = 'stage.started',
  STAGE_COMPLETED = 'stage.completed',
  STAGE_FAILED = 'stage.failed',

  // Agent events
  AGENT_STARTED = 'agent.started',
  AGENT_COMPLETED = 'agent.completed',

  // Connection events
  CONNECTION_ACK = 'connection.ack',
  SUBSCRIPTION_ACK = 'subscription.ack',

  // HITL events (for future use in PR#12)
  HUMAN_INPUT_REQUIRED = 'human_input.required',
  HUMAN_INPUT_RECEIVED = 'human_input.received',
  HUMAN_INPUT_TIMEOUT = 'human_input.timeout',
}

/**
 * Workflow event data structure (matches backend structure)
 */
export interface WorkflowEvent {
  event_type: WorkflowEventType;
  workflow_id: string;
  conversation_id?: string;
  timestamp: string;

  // Event-specific fields (at root level, matching backend)
  stage?: string;        // analysis, deciding, visualizing, finalizing
  agent?: string;        // analysis, visualization
  progress?: number;     // 0.0 - 1.0
  message?: string;      // Human-readable message
  error?: string;        // Error message (if failed)

  // Additional data (optional nested object)
  data?: {
    [key: string]: any;
  };
}

/**
 * Callback function type for event handlers
 */
type EventCallback = (event: WorkflowEvent) => void;

/**
 * WebSocket Service Class
 *
 * Singleton service for managing WebSocket connections to the backend.
 * Handles connection lifecycle, event subscription, and automatic reconnection.
 *
 * @example
 * ```typescript
 * // Connect to WebSocket
 * await websocketService.connect();
 *
 * // Subscribe to workflow events
 * const workflowId = 'workflow-123';
 * websocketService.subscribe(workflowId);
 *
 * // Listen for events
 * websocketService.on(workflowId, (event) => {
 *   console.log('Event:', event.event_type);
 * });
 *
 * // Unsubscribe when done
 * websocketService.unsubscribe(workflowId);
 * ```
 */
class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private eventCallbacks: Map<string, EventCallback[]> = new Map();
  private subscribedWorkflows: Set<string> = new Set();
  private isConnecting = false;
  private pingInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private connectionFailed = false;

  /**
   * Connect to WebSocket server with JWT authentication
   *
   * @throws {Error} If no authentication token is found
   */
  async connect(): Promise<void> {
    // Don't attempt connection if already failed
    if (this.connectionFailed) {
      console.log('[WebSocket] Connection disabled due to previous failures');
      return;
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected');
      return;
    }

    if (this.isConnecting) {
      console.log('[WebSocket] Connection already in progress');
      return;
    }

    this.isConnecting = true;

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        console.error('[WebSocket] No authentication token found in localStorage');
        this.isConnecting = false;
        this.connectionFailed = true;
        throw new Error('No authentication token found');
      }

      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
      // Note: Don't add /ws here if NEXT_PUBLIC_WS_URL already includes it
      const url = `${wsUrl}?token=${token}`;

      console.log('[WebSocket] Attempting connection to:', wsUrl);
      console.log('[WebSocket] Token available:', token ? 'Yes (length: ' + token.length + ')' : 'No');
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        this.reconnectAttempts = 0;
        this.isConnecting = false;

        // Re-subscribe to workflows after reconnection
        if (this.subscribedWorkflows.size > 0) {
          console.log('[WebSocket] Re-subscribing to', this.subscribedWorkflows.size, 'workflows');
          this.subscribedWorkflows.forEach(workflowId => {
            this.subscribe(workflowId);
          });
        }

        // Start ping interval to keep connection alive
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: WorkflowEvent = JSON.parse(event.data);
          this.handleEvent(data);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
          console.error('[WebSocket] Raw message:', event.data);
        }
      };

      this.ws.onerror = (error: Event) => {
        console.error('[WebSocket] Connection error occurred. This usually means:');
        console.error('  1. Backend WebSocket server is not running');
        console.error('  2. CORS/network policy blocking connection');
        console.error('  3. Invalid authentication token');
        console.error('  WebSocket URL:', wsUrl);
      };

      this.ws.onclose = (event) => {
        const closeReasons: Record<number, string> = {
          1000: 'Normal closure',
          1001: 'Going away',
          1006: 'Abnormal closure (no close frame)',
          1008: 'Policy violation (likely auth failure)',
          1011: 'Server error',
        };

        const reason = closeReasons[event.code] || 'Unknown reason';
        console.log('[WebSocket] Disconnected');
        console.log('  Close code:', event.code, `(${reason})`);
        console.log('  Reason:', event.reason || 'No reason provided');

        this.isConnecting = false;
        this.ws = null;
        this.stopPingInterval();

        // Attempt reconnection if not a normal closure
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          const delay = this.reconnectDelay * this.reconnectAttempts;
          console.log(`[WebSocket] Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

          this.reconnectTimeout = setTimeout(() => {
            this.connect().catch(console.error);
          }, delay);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.warn('[WebSocket] Max reconnection attempts reached.');
          console.warn('[WebSocket] The app will continue to work, but without real-time progress updates.');
          console.warn('[WebSocket] Please check:');
          console.warn('  1. Backend is running and accessible');
          console.warn('  2. WebSocket endpoint is correct:', wsUrl);
          console.warn('  3. Authentication token is valid');
          this.connectionFailed = true;
        }
      };
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      this.isConnecting = false;
      throw error;
    }
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    // Send ping every 30 seconds
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ action: 'ping' }));
        } catch (error) {
          console.error('[WebSocket] Failed to send ping:', error);
        }
      }
    }, 30000);
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Subscribe to workflow events
   *
   * @param workflowId - The workflow ID to subscribe to
   */
  subscribe(workflowId: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Not connected, queuing subscription for:', workflowId);
      this.subscribedWorkflows.add(workflowId);
      return;
    }

    const message = {
      action: 'subscribe',
      workflow_id: workflowId,
    };

    try {
      this.ws.send(JSON.stringify(message));
      this.subscribedWorkflows.add(workflowId);
      console.log('[WebSocket] Subscribed to workflow:', workflowId);
    } catch (error) {
      console.error('[WebSocket] Failed to subscribe:', error);
    }
  }

  /**
   * Unsubscribe from workflow events
   *
   * @param workflowId - The workflow ID to unsubscribe from
   */
  unsubscribe(workflowId: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Not connected, cannot unsubscribe from:', workflowId);
      this.subscribedWorkflows.delete(workflowId);
      this.eventCallbacks.delete(workflowId);
      return;
    }

    const message = {
      action: 'unsubscribe',
      workflow_id: workflowId,
    };

    try {
      this.ws.send(JSON.stringify(message));
      this.subscribedWorkflows.delete(workflowId);
      this.eventCallbacks.delete(workflowId);
      console.log('[WebSocket] Unsubscribed from workflow:', workflowId);
    } catch (error) {
      console.error('[WebSocket] Failed to unsubscribe:', error);
    }
  }

  /**
   * Register callback for workflow events
   *
   * @param workflowId - The workflow ID to listen to
   * @param callback - The callback function to invoke on events
   */
  on(workflowId: string, callback: EventCallback): void {
    if (!this.eventCallbacks.has(workflowId)) {
      this.eventCallbacks.set(workflowId, []);
    }
    this.eventCallbacks.get(workflowId)?.push(callback);
    console.log('[WebSocket] Registered callback for workflow:', workflowId);
  }

  /**
   * Remove callback for workflow events
   *
   * @param workflowId - The workflow ID to remove callback from
   * @param callback - The specific callback to remove (optional, removes all if not provided)
   */
  off(workflowId: string, callback?: EventCallback): void {
    if (!callback) {
      this.eventCallbacks.delete(workflowId);
      console.log('[WebSocket] Removed all callbacks for workflow:', workflowId);
      return;
    }

    const callbacks = this.eventCallbacks.get(workflowId);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
        console.log('[WebSocket] Removed callback for workflow:', workflowId);
      }

      // Clean up empty callback arrays
      if (callbacks.length === 0) {
        this.eventCallbacks.delete(workflowId);
      }
    }
  }

  /**
   * Handle incoming WebSocket events
   *
   * @param event - The workflow event received from backend
   */
  private handleEvent(event: WorkflowEvent): void {
    // Validate event structure
    if (!event || !event.event_type) {
      console.warn('[WebSocket] Received invalid event:', event);
      return;
    }

    // Log connection events differently
    if (event.event_type === WorkflowEventType.CONNECTION_ACK ||
        event.event_type === WorkflowEventType.SUBSCRIPTION_ACK) {
      const message = event.message || '';
      console.log('[WebSocket]', event.event_type, message);
      return;
    }

    console.log('[WebSocket] Event:', event.event_type, 'for workflow:', event.workflow_id);

    const callbacks = this.eventCallbacks.get(event.workflow_id);
    if (callbacks && callbacks.length > 0) {
      callbacks.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error('[WebSocket] Error in callback:', error);
        }
      });
    } else {
      console.warn('[WebSocket] No callbacks registered for workflow:', event.workflow_id);
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    console.log('[WebSocket] Disconnecting...');

    // Clear reconnection timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    // Stop ping interval
    this.stopPingInterval();

    // Close WebSocket
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    // Clear state
    this.subscribedWorkflows.clear();
    this.eventCallbacks.clear();
    this.reconnectAttempts = 0;
    this.isConnecting = false;

    console.log('[WebSocket] Disconnected');
  }

  /**
   * Check if WebSocket is connected
   *
   * @returns True if WebSocket is open, false otherwise
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current connection state
   *
   * @returns Connection state string
   */
  getConnectionState(): string {
    if (!this.ws) return 'disconnected';

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'closed';
      default:
        return 'unknown';
    }
  }

  /**
   * Get number of subscribed workflows
   *
   * @returns Number of active subscriptions
   */
  getSubscriptionCount(): number {
    return this.subscribedWorkflows.size;
  }
}

/**
 * Singleton instance of WebSocket service
 */
export const websocketService = new WebSocketService();
