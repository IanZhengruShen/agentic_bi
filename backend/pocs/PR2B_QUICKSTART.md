# PR#2B Quick Start Guide

## POCs in This PR

1. **LangGraph Workflow POC** - Multi-step AI agent workflow with Langfuse tracing
2. **WebSocket Server POC** - Real-time bidirectional communication
3. **End-to-End POC** - Complete integration: Query → LangGraph → Langfuse → WebSocket

## Prerequisites

Same as PR#2A:
- uv installed
- Azure OpenAI credentials configured in `../.env`
- Langfuse credentials configured in `../.env`

## Running the POCs

### 1. LangGraph Workflow POC

Tests LangGraph workflow with Langfuse tracing:

```bash
# From backend/ directory
uv run python pocs/langgraph_workflow_poc.py
```

**Expected Output:**
- Workflow creates multi-step agent flow
- Each step traced in Langfuse
- SQL query generated based on intent
- Langfuse trace URL displayed

### 2. WebSocket Server POC

Tests real-time communication:

```bash
# From backend/ directory
uv run python pocs/websocket_server_poc.py
```

**Then:**
1. Server starts on http://localhost:8080
2. Open http://localhost:8080 in your browser
3. Test sending queries and broadcasts
4. Open multiple tabs to see real-time sync

**Features:**
- Auto-reconnection
- Query processing with progress updates
- Broadcast messages to all clients
- Ping/pong heartbeat

### 3. End-to-End POC (⭐ RECOMMENDED)

Complete integration demonstration:

```bash
# From backend/ directory
uv run python pocs/end_to_end_poc.py
```

**Then:**
1. Server starts on http://localhost:8081
2. Open http://localhost:8081 in your browser
3. Enter a natural language query
4. Watch real-time progress:
   - Initializing (5%)
   - Analyzing intent (40%)
   - Generating SQL (70%)
   - Formatting results (100%)
5. View results and Langfuse trace link

**What It Demonstrates:**
```
User Query
  ↓ (WebSocket)
LangGraph Workflow
  ├─ Intent Classification (traced)
  ├─ SQL Generation (traced)
  └─ Result Formatting (traced)
  ↓ (WebSocket progress updates)
Client Receives Results + Trace URL
```

## Verification

### For LangGraph POC:
1. Check console output for workflow steps
2. Open Langfuse trace URL
3. Verify all LLM calls are captured
4. Check workflow state transitions

### For WebSocket POC:
1. Open browser developer console
2. Verify WebSocket connection established
3. Test query processing
4. Test broadcast messages
5. Open multiple tabs to verify broadcasting

### For End-to-End POC:
1. Submit query via web interface
2. Watch real-time progress bar
3. Verify results displayed correctly
4. Click "View Trace" link
5. Confirm all steps in Langfuse

## What's Different from PR#2A?

**PR#2A:**
- Individual service integrations
- Standalone scripts
- No real-time communication

**PR#2B:**
- Multi-step workflows
- Real-time progress updates
- Complete system integration
- Ready for production patterns

## Troubleshooting

### "Module 'langgraph' not found"

```bash
# LangGraph is already in dependencies
uv sync
```

### "Module 'socketio' not found"

```bash
# python-socketio is already in dependencies
uv sync
```

### "Address already in use"

Another server is using the port:

```bash
# For WebSocket POC (port 8080)
lsof -ti:8080 | xargs kill -9

# For End-to-End POC (port 8081)
lsof -ti:8081 | xargs kill -9
```

### WebSocket connection fails

1. Check server is running
2. Clear browser cache
3. Try different browser
4. Check firewall settings

## Architecture Notes

### LangGraph State Management

```python
class WorkflowState(TypedDict):
    query: str
    intent: str
    sql_query: str
    result: str
    messages: Annotated[list, operator.add]  # Accumulates across nodes
```

### WebSocket Event Flow

```
Client                Server
  |                     |
  |---connect---------->|
  |<--connection_resp---|
  |                     |
  |---query_request---->|
  |<--query_status------| (25%)
  |<--query_status------| (50%)
  |<--query_status------| (75%)
  |<--query_result------| (100%)
```

### Langfuse Integration Pattern

```python
# Create handler
handler = CallbackHandler(
    public_key=config["langfuse_public_key"],
    secret_key=config["langfuse_secret_key"],
    trace_name="workflow_name",
    user_id="user_id",
)

# Use in LLM calls
llm.invoke(messages, config={"callbacks": [handler]})

# Get trace URL
trace_url = handler.trace.get_trace_url()

# Flush before ending
handler.flush()
```

## Next Steps

After PR#2B validation:

1. Merge to main
2. Proceed to **PR#3: Authentication & Authorization**
   - User authentication
   - OPA integration
   - JWT token management

## Success Criteria

✅ LangGraph workflow creates multi-step flow
✅ Langfuse traces entire workflow
✅ WebSocket server handles multiple clients
✅ Real-time progress updates work
✅ End-to-end integration functional
✅ All traces visible in Langfuse dashboard

Ready to build the real platform!
