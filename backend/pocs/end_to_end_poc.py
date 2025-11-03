"""
End-to-End POC: Query → LangGraph → Langfuse → WebSocket

This POC demonstrates the complete integration:
1. Receive user query via WebSocket
2. Process through LangGraph workflow
3. Trace everything with Langfuse
4. Send real-time progress updates via WebSocket
5. Return final results to client

This is the integration pattern for the full Agentic BI Platform.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, TypedDict, Annotated
import operator

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import socketio
from aiohttp import web
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langfuse.callback import CallbackHandler


# Workflow State
class QueryState(TypedDict):
    """State for query processing workflow."""
    query: str
    intent: str
    sql_query: str
    result: str
    error: str
    progress: int
    messages: Annotated[list, operator.add]


# Load configuration
def load_config() -> Dict[str, str]:
    """Load configuration from environment."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    return {
        "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
        "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
        "langfuse_public_key": os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        "langfuse_secret_key": os.getenv("LANGFUSE_SECRET_KEY", ""),
        "langfuse_host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    }


# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=False
)

app = web.Application()
sio.attach(app)

# Store config globally (for POC simplicity)
config = load_config()


async def emit_progress(sid: str, status: str, message: str, progress: int, extra: Dict = None):
    """Helper to emit progress updates."""
    data = {
        'status': status,
        'message': message,
        'progress': progress,
    }
    if extra:
        data.update(extra)
    await sio.emit('workflow_progress', data, to=sid)


async def process_query_workflow(sid: str, query: str):
    """
    Process query through LangGraph workflow with WebSocket updates.

    This demonstrates the full integration pattern.
    """
    try:
        # Initialize Langfuse
        await emit_progress(sid, 'initializing', 'Initializing tracing...', 5)

        langfuse_handler = CallbackHandler(
            public_key=config["langfuse_public_key"],
            secret_key=config["langfuse_secret_key"],
            host=config["langfuse_host"],
            trace_name=f"end_to_end_query_{sid[:8]}",
            user_id=sid,
        )

        # Initialize LLM
        await emit_progress(sid, 'initializing', 'Setting up AI models...', 10)

        llm = AzureChatOpenAI(
            azure_endpoint=config["azure_endpoint"],
            api_key=config["azure_api_key"],
            api_version=config["azure_api_version"],
            deployment_name=config["azure_deployment"],
            temperature=0.7,
            max_tokens=200,
        )

        # Build workflow
        await emit_progress(sid, 'analyzing', 'Analyzing query intent...', 20)

        async def classify_intent_node(state: QueryState) -> QueryState:
            """Classify intent with progress update."""
            messages = [
                SystemMessage(content="Classify this query as 'analytics', 'reporting', or 'exploration'. "
                                    "Respond with only one word."),
                HumanMessage(content=state['query'])
            ]

            response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
            intent = response.content.strip().lower()

            # Send progress update
            await emit_progress(sid, 'analyzing', f'Intent identified: {intent}', 40)

            return {
                **state,
                "intent": intent,
                "progress": 40,
                "messages": [f"Intent: {intent}"]
            }

        async def generate_sql_node(state: QueryState) -> QueryState:
            """Generate SQL with progress update."""
            await emit_progress(sid, 'generating', 'Generating SQL query...', 60)

            messages = [
                SystemMessage(content="Generate a simple educational SQL query. Return only the query."),
                HumanMessage(content=state['query'])
            ]

            response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
            sql = response.content.strip()

            await emit_progress(sid, 'generating', 'SQL query generated', 70)

            return {
                **state,
                "sql_query": sql,
                "progress": 70,
                "messages": ["SQL generated"]
            }

        async def format_result_node(state: QueryState) -> QueryState:
            """Format final result."""
            await emit_progress(sid, 'finalizing', 'Formatting results...', 90)

            result = {
                "query": state['query'],
                "intent": state['intent'],
                "sql": state['sql_query'],
                "steps": state['messages']
            }

            return {
                **state,
                "result": str(result),
                "progress": 100,
                "messages": ["Complete"]
            }

        # Create workflow (synchronous LangGraph)
        workflow = StateGraph(QueryState)
        workflow.add_node("classify", lambda s: asyncio.run(classify_intent_node(s)))
        workflow.add_node("generate", lambda s: asyncio.run(generate_sql_node(s)))
        workflow.add_node("format", lambda s: asyncio.run(format_result_node(s)))

        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "generate")
        workflow.add_edge("generate", "format")
        workflow.add_edge("format", END)

        # Execute workflow
        await emit_progress(sid, 'processing', 'Running workflow...', 30)

        app_compiled = workflow.compile()
        initial_state: QueryState = {
            "query": query,
            "intent": "",
            "sql_query": "",
            "result": "",
            "error": "",
            "progress": 0,
            "messages": [],
        }

        # Run in thread pool to avoid blocking
        final_state = await asyncio.get_event_loop().run_in_executor(
            None, app_compiled.invoke, initial_state
        )

        # Get trace URL
        trace_url = None
        if hasattr(langfuse_handler, 'trace'):
            trace_url = langfuse_handler.trace.get_trace_url()

        # Send final result
        await emit_progress(sid, 'completed', 'Query completed!', 100, {
            'query': final_state['query'],
            'intent': final_state['intent'],
            'sql': final_state['sql_query'],
            'trace_url': trace_url
        })

        # Flush Langfuse
        langfuse_handler.flush()

    except Exception as e:
        await emit_progress(sid, 'error', f'Error: {str(e)}', 0, {'error': str(e)})


# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"[E2E] Client connected: {sid}")
    await sio.emit('connection_response', {
        'status': 'connected',
        'message': 'Connected to End-to-End POC Server',
        'sid': sid
    }, to=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"[E2E] Client disconnected: {sid}")


@sio.event
async def process_query(sid, data):
    """Process query through full workflow."""
    query = data.get('query', '')
    print(f"[E2E] Processing query from {sid}: {query}")

    # Process in background task
    asyncio.create_task(process_query_workflow(sid, query))


# HTTP route for client
async def index(request):
    """Serve end-to-end POC client."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>End-to-End POC</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 900px;
                margin: 30px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
            }
            .status {
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                font-weight: bold;
                text-align: center;
            }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .query-section {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }
            input {
                width: 100%;
                padding: 15px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                margin: 10px 0;
            }
            button {
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                margin: 10px 0;
            }
            button:hover { opacity: 0.9; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            .progress-section {
                margin: 20px 0;
            }
            .progress-bar {
                width: 100%;
                height: 30px;
                background: #e9ecef;
                border-radius: 15px;
                overflow: hidden;
                position: relative;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transition: width 0.5s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
            }
            .progress-text {
                margin-top: 10px;
                text-align: center;
                color: #666;
                font-size: 14px;
            }
            .result-section {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                display: none;
            }
            .result-section.show { display: block; }
            .result-item {
                margin: 10px 0;
                padding: 10px;
                background: white;
                border-radius: 4px;
            }
            .result-label {
                font-weight: bold;
                color: #667eea;
            }
            .trace-link {
                display: inline-block;
                margin-top: 10px;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
            .trace-link:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 End-to-End Integration POC</h1>
            <p class="subtitle">Query → LangGraph → Langfuse → WebSocket</p>

            <div id="status" class="status disconnected">Disconnected</div>

            <div class="query-section">
                <h2>Ask Your Question</h2>
                <input type="text" id="queryInput"
                       placeholder="e.g., Show me total sales for Q4 2024"
                       value="Show me the top performing products this quarter">
                <button id="sendQuery">Process Query</button>
            </div>

            <div class="progress-section" id="progressSection" style="display:none;">
                <h2>Processing...</h2>
                <div class="progress-bar">
                    <div id="progress" class="progress-fill" style="width: 0%">0%</div>
                </div>
                <div id="progressText" class="progress-text">Initializing...</div>
            </div>

            <div class="result-section" id="resultSection">
                <h2>✅ Results</h2>
                <div class="result-item">
                    <div class="result-label">Query:</div>
                    <div id="resultQuery"></div>
                </div>
                <div class="result-item">
                    <div class="result-label">Intent:</div>
                    <div id="resultIntent"></div>
                </div>
                <div class="result-item">
                    <div class="result-label">Generated SQL:</div>
                    <pre id="resultSQL"></pre>
                </div>
                <div class="result-item">
                    <div class="result-label">Langfuse Trace:</div>
                    <a id="traceLink" class="trace-link" target="_blank">View Trace →</a>
                </div>
            </div>
        </div>

        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <script>
            const socket = io();
            const statusEl = document.getElementById('status');
            const queryInput = document.getElementById('queryInput');
            const sendBtn = document.getElementById('sendQuery');
            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('progress');
            const progressText = document.getElementById('progressText');
            const resultSection = document.getElementById('resultSection');

            socket.on('connect', () => {
                statusEl.textContent = `Connected (ID: ${socket.id.slice(0,8)}...)`;
                statusEl.className = 'status connected';
            });

            socket.on('disconnect', () => {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'status disconnected';
            });

            socket.on('workflow_progress', (data) => {
                progressSection.style.display = 'block';
                progressFill.style.width = data.progress + '%';
                progressFill.textContent = data.progress + '%';
                progressText.textContent = data.message;

                if (data.status === 'completed') {
                    // Show results
                    document.getElementById('resultQuery').textContent = data.query;
                    document.getElementById('resultIntent').textContent = data.intent;
                    document.getElementById('resultSQL').textContent = data.sql;

                    if (data.trace_url) {
                        const traceLink = document.getElementById('traceLink');
                        traceLink.href = data.trace_url;
                        traceLink.style.display = 'inline-block';
                    }

                    resultSection.classList.add('show');
                    sendBtn.disabled = false;

                    setTimeout(() => {
                        progressSection.style.display = 'none';
                    }, 2000);
                } else if (data.status === 'error') {
                    alert('Error: ' + data.error);
                    sendBtn.disabled = false;
                    progressSection.style.display = 'none';
                }
            });

            sendBtn.addEventListener('click', () => {
                const query = queryInput.value.trim();
                if (query) {
                    resultSection.classList.remove('show');
                    sendBtn.disabled = true;
                    progressSection.style.display = 'block';
                    progressFill.style.width = '0%';
                    socket.emit('process_query', { query });
                }
            });
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


app.router.add_get('/', index)


async def start_server(host='0.0.0.0', port=8081):
    """Start the end-to-end POC server."""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"""
============================================================
End-to-End POC Server Started
============================================================

🚀 Server running at: http://{host}:{port}

This POC demonstrates:
✓ Query processing through LangGraph workflow
✓ Real-time progress updates via WebSocket
✓ Complete Langfuse tracing
✓ Multi-step AI agent workflow

To test:
1. Open http://localhost:{port} in your browser
2. Enter a natural language query
3. Click "Process Query"
4. Watch real-time progress updates
5. View results and Langfuse trace

Press Ctrl+C to stop
============================================================
    """)


def main():
    """Run the end-to-end POC server."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
