"""
WebSocket Server POC

This POC demonstrates:
1. Python Socket.IO server setup
2. Real-time bi-directional communication
3. Event handling (connect, disconnect, custom events)
4. Broadcasting messages to clients
"""

import asyncio
from typing import Dict, Any
import socketio
from aiohttp import web


# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',  # For POC only - restrict in production
    logger=True,
    engineio_logger=False
)

app = web.Application()
sio.attach(app)


# Connection event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"[WebSocket] Client connected: {sid}")
    await sio.emit('connection_response', {
        'status': 'connected',
        'message': 'Welcome to Agentic BI WebSocket Server!',
        'sid': sid
    }, to=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"[WebSocket] Client disconnected: {sid}")


# Custom event handlers
@sio.event
async def query_request(sid, data):
    """Handle query request from client."""
    print(f"[WebSocket] Query request from {sid}: {data}")

    query = data.get('query', '')

    # Simulate processing with progress updates
    await sio.emit('query_status', {
        'status': 'processing',
        'message': 'Analyzing query...',
        'progress': 25
    }, to=sid)

    await asyncio.sleep(0.5)

    await sio.emit('query_status', {
        'status': 'processing',
        'message': 'Generating SQL...',
        'progress': 50
    }, to=sid)

    await asyncio.sleep(0.5)

    await sio.emit('query_status', {
        'status': 'processing',
        'message': 'Executing query...',
        'progress': 75
    }, to=sid)

    await asyncio.sleep(0.5)

    # Send final result
    await sio.emit('query_result', {
        'status': 'completed',
        'query': query,
        'result': f"Results for: {query}",
        'progress': 100
    }, to=sid)

    print(f"[WebSocket] Query completed for {sid}")


@sio.event
async def ping(sid, data):
    """Handle ping request."""
    print(f"[WebSocket] Ping from {sid}")
    await sio.emit('pong', {'timestamp': data.get('timestamp')}, to=sid)


@sio.event
async def broadcast_message(sid, data):
    """Broadcast message to all connected clients."""
    message = data.get('message', '')
    print(f"[WebSocket] Broadcasting from {sid}: {message}")
    await sio.emit('broadcast', {
        'from': sid,
        'message': message
    }, skip_sid=sid)  # Don't send to sender


# HTTP routes
async def index(request):
    """Serve a simple test page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket POC Client</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
                font-weight: bold;
            }
            .connected {
                background: #d4edda;
                color: #155724;
            }
            .disconnected {
                background: #f8d7da;
                color: #721c24;
            }
            input, textarea, button {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            button {
                background: #007bff;
                color: white;
                border: none;
                cursor: pointer;
                font-weight: bold;
            }
            button:hover {
                background: #0056b3;
            }
            button:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            #log {
                background: #f8f9fa;
                padding: 15px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                max-height: 300px;
                overflow-y: auto;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
            .log-entry {
                margin: 5px 0;
                padding: 5px;
                border-bottom: 1px solid #e9ecef;
            }
            .log-success { color: #28a745; }
            .log-error { color: #dc3545; }
            .log-info { color: #007bff; }
            .progress-bar {
                width: 100%;
                height: 20px;
                background: #e9ecef;
                border-radius: 4px;
                overflow: hidden;
                margin: 10px 0;
            }
            .progress-fill {
                height: 100%;
                background: #007bff;
                transition: width 0.3s ease;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 WebSocket POC Client</h1>

            <div id="status" class="status disconnected">Disconnected</div>

            <h2>Query Test</h2>
            <input type="text" id="queryInput" placeholder="Enter your query..." value="Show me sales data">
            <div class="progress-bar">
                <div id="progress" class="progress-fill" style="width: 0%"></div>
            </div>
            <button id="sendQuery">Send Query</button>

            <h2>Broadcast Test</h2>
            <input type="text" id="broadcastInput" placeholder="Message to broadcast...">
            <button id="sendBroadcast">Broadcast</button>

            <h2>Event Log</h2>
            <div id="log"></div>
        </div>

        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <script>
            const socket = io();
            const statusEl = document.getElementById('status');
            const logEl = document.getElementById('log');
            const progressEl = document.getElementById('progress');
            const queryInput = document.getElementById('queryInput');
            const broadcastInput = document.getElementById('broadcastInput');

            function addLog(message, type = 'info') {
                const entry = document.createElement('div');
                entry.className = `log-entry log-${type}`;
                entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
                logEl.insertBefore(entry, logEl.firstChild);
            }

            // Connection events
            socket.on('connect', () => {
                statusEl.textContent = `Connected (ID: ${socket.id})`;
                statusEl.className = 'status connected';
                addLog('Connected to WebSocket server', 'success');
            });

            socket.on('disconnect', () => {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'status disconnected';
                addLog('Disconnected from server', 'error');
                progressEl.style.width = '0%';
            });

            socket.on('connection_response', (data) => {
                addLog(`Server: ${data.message}`, 'success');
            });

            // Query events
            socket.on('query_status', (data) => {
                addLog(`${data.message} (${data.progress}%)`, 'info');
                progressEl.style.width = data.progress + '%';
            });

            socket.on('query_result', (data) => {
                addLog(`Query completed: ${data.result}`, 'success');
                progressEl.style.width = data.progress + '%';
                setTimeout(() => {
                    progressEl.style.width = '0%';
                }, 2000);
            });

            // Broadcast events
            socket.on('broadcast', (data) => {
                addLog(`Broadcast from ${data.from}: ${data.message}`, 'info');
            });

            // Ping/pong
            socket.on('pong', (data) => {
                addLog('Pong received', 'info');
            });

            // Button handlers
            document.getElementById('sendQuery').addEventListener('click', () => {
                const query = queryInput.value.trim();
                if (query) {
                    addLog(`Sending query: ${query}`, 'info');
                    socket.emit('query_request', { query });
                    progressEl.style.width = '0%';
                }
            });

            document.getElementById('sendBroadcast').addEventListener('click', () => {
                const message = broadcastInput.value.trim();
                if (message) {
                    addLog(`Broadcasting: ${message}`, 'info');
                    socket.emit('broadcast_message', { message });
                    broadcastInput.value = '';
                }
            });

            // Test ping every 5 seconds
            setInterval(() => {
                if (socket.connected) {
                    socket.emit('ping', { timestamp: Date.now() });
                }
            }, 5000);
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


# Add routes
app.router.add_get('/', index)


async def start_server(host='0.0.0.0', port=8080):
    """Start the WebSocket server."""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"""
========================================================
WebSocket Server POC Started
========================================================

Server running at: http://{host}:{port}

To test:
1. Open http://localhost:{port} in your browser
2. The client will auto-connect
3. Try sending queries and broadcast messages
4. Open multiple browser tabs to see broadcasts

Press Ctrl+C to stop
========================================================
    """)


def main():
    """Run the WebSocket server POC."""
    try:
        # Start server
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
