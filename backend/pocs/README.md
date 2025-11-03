# PR#2A: Core Integration POCs

This directory contains Proof of Concept (POC) implementations for the core integrations required by the Agentic BI Platform.

## Overview

PR#2A validates three critical integrations that form the foundation of the platform:

1. **Azure OpenAI** - LLM capabilities for natural language understanding and generation
2. **MindsDB** - SQL database integration for data querying
3. **Langfuse** - Observability and tracing for LLM operations

## Prerequisites

Before running the POCs, ensure you have:

1. **Python 3.12+** installed
2. **Environment Variables** configured (see Configuration section)
3. **External Services** accessible:
   - Azure OpenAI endpoint with valid API key
   - MindsDB instance (no authentication required for MVP)
   - Langfuse account with public and secret keys

## Configuration

### 1. Create .env file

Copy `.env.example` to `.env` in the project root:

```bash
cp ../.env.example ../.env
```

### 2. Configure Azure OpenAI

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-actual-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2023-05-15
```

**How to obtain:**
- Go to Azure Portal → Azure OpenAI Service
- Copy the endpoint URL and API key
- Note your deployment name (e.g., "gpt-4")

### 3. Configure MindsDB

```bash
# MindsDB Configuration
MINDSDB_API_URL=https://your-mindsdb-instance.com
```

**How to obtain:**
- Use MindsDB Cloud or self-hosted instance
- No authentication required for MVP
- Ensure the instance is accessible from your network

### 4. Configure Langfuse

```bash
# Langfuse Configuration
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-your-actual-key
LANGFUSE_SECRET_KEY=sk-lf-your-actual-key
```

**How to obtain:**
- Sign up at https://cloud.langfuse.com
- Create a new project
- Copy the public and secret keys from Settings → API Keys

## Installation

Install dependencies from the project root:

```bash
cd ..
pip install -e .
```

Or install with development dependencies:

```bash
pip install -e ".[dev]"
```

## Running the POCs

### Option 1: Run Individual POCs

Each POC can be run independently to test a specific integration:

#### Azure OpenAI POC

```bash
cd backend/pocs
python azure_openai_poc.py
```

**Expected Output:**
- Configuration validation
- Successful LLM completion
- Token usage statistics

#### MindsDB POC

```bash
python mindsdb_poc.py
```

**Expected Output:**
- Health check status
- List of databases
- List of tables (if available)

#### Langfuse POC

```bash
python langfuse_poc.py
```

**Expected Output:**
- Trace creation confirmation
- Callback handler setup
- Langfuse dashboard URLs for verification

#### Combined POC (Recommended)

```bash
python combined_llm_langfuse_poc.py
```

**Expected Output:**
- Full integration test
- LLM calls with Langfuse tracing
- Multiple calls in single trace session
- Dashboard verification instructions

### Option 2: Run All POCs Sequentially

Create a test runner script:

```bash
#!/bin/bash
echo "Running PR#2A POCs..."
python azure_openai_poc.py && \
python mindsdb_poc.py && \
python langfuse_poc.py && \
python combined_llm_langfuse_poc.py
```

## Running Tests

Execute the test suite:

```bash
cd backend
pytest tests/pocs/ -v
```

Run with coverage:

```bash
pytest tests/pocs/ -v --cov=pocs --cov-report=term-missing
```

## Connection Patterns

### Pattern 1: Azure OpenAI Direct Connection

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=config["api_key"],
    api_version=config["api_version"],
    azure_endpoint=config["endpoint"],
)

response = client.chat.completions.create(
    model=config["deployment"],
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Your question here"}
    ],
    max_tokens=150,
    temperature=0.7,
)
```

**Key Points:**
- Use `AzureOpenAI` class (not standard `OpenAI`)
- Specify `azure_endpoint` instead of `base_url`
- Use `deployment_name` for model selection
- Track token usage from `response.usage`

### Pattern 2: LangChain with Azure OpenAI

```python
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

llm = AzureChatOpenAI(
    azure_endpoint=config["azure_endpoint"],
    api_key=config["azure_api_key"],
    api_version=config["azure_api_version"],
    deployment_name=config["azure_deployment"],
    temperature=0.7,
)

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Your question here"),
]

response = llm.invoke(messages)
```

**Key Points:**
- Use `AzureChatOpenAI` from `langchain_openai`
- Messages use `SystemMessage` and `HumanMessage` classes
- Compatible with LangChain callbacks and chains

### Pattern 3: MindsDB HTTP Client

```python
import httpx

class MindsDBClient:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.client = httpx.Client(timeout=30.0)

    def execute_query(self, query: str) -> dict:
        endpoint = f"{self.api_url}/api/sql/query"
        response = self.client.post(
            endpoint,
            json={"query": query},
            headers={"Content-Type": "application/json"},
        )
        return response.json()
```

**Key Points:**
- Use HTTP API (no authentication for MVP)
- Endpoint: `/api/sql/query`
- Send SQL queries as JSON payload
- Handle timeouts (30s recommended)

### Pattern 4: Langfuse Direct Client

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=config["public_key"],
    secret_key=config["secret_key"],
    host=config["host"],
)

trace = langfuse.trace(
    name="operation_name",
    user_id="user_id",
    metadata={"key": "value"},
    tags=["tag1", "tag2"],
)

generation = trace.generation(
    name="llm_call",
    model="gpt-4",
    input="prompt",
    output="response",
)

langfuse.flush()  # Ensure data is sent
```

**Key Points:**
- Create traces for high-level operations
- Add generations for LLM calls
- Include metadata and tags for filtering
- Always call `flush()` to ensure data is sent

### Pattern 5: Langfuse with LangChain Callback

```python
from langfuse.callback import CallbackHandler

handler = CallbackHandler(
    public_key=config["public_key"],
    secret_key=config["secret_key"],
    host=config["host"],
    trace_name="operation_name",
    user_id="user_id",
    metadata={"key": "value"},
    tags=["tag1", "tag2"],
)

# Use with LangChain
response = llm.invoke(
    messages,
    config={"callbacks": [handler]}
)

handler.flush()  # Ensure trace is sent
```

**Key Points:**
- Use `CallbackHandler` for automatic LangChain integration
- Traces are created automatically
- All LLM calls are captured with input/output
- Token usage is tracked automatically
- Can reuse handler for multiple calls in same trace

## Troubleshooting

### Azure OpenAI Issues

**Problem:** `Authentication failed`
- **Solution:** Verify `AZURE_OPENAI_API_KEY` is correct
- **Check:** Ensure API key has not expired in Azure Portal

**Problem:** `Resource not found`
- **Solution:** Verify `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT`
- **Check:** Ensure deployment name matches exactly (case-sensitive)

**Problem:** `Rate limit exceeded`
- **Solution:** Implement retry logic with exponential backoff
- **Check:** Review quota limits in Azure Portal

### MindsDB Issues

**Problem:** `Connection refused`
- **Solution:** Verify MindsDB instance is running
- **Check:** Test URL in browser: `https://your-instance/api/status`

**Problem:** `HTTP 500 errors`
- **Solution:** Check MindsDB logs for detailed error messages
- **Check:** Verify SQL query syntax is correct

### Langfuse Issues

**Problem:** `Authentication failed`
- **Solution:** Verify public and secret keys are correct
- **Check:** Ensure keys are not the placeholder values (`pk-lf-xxx`)

**Problem:** `Traces not appearing in dashboard`
- **Solution:** Ensure `flush()` is called after creating traces
- **Check:** Wait a few seconds for data to sync
- **Check:** Verify you're looking at the correct project

**Problem:** `Callback handler not capturing traces`
- **Solution:** Ensure handler is passed to LangChain via `config` parameter
- **Check:** Verify LangChain version is compatible with Langfuse

## Success Criteria

PR#2A is considered successful when:

- ✅ All POCs run without errors
- ✅ Azure OpenAI returns valid completions
- ✅ Token usage is tracked correctly
- ✅ MindsDB connection is established
- ✅ Database/table discovery works
- ✅ Langfuse traces are created
- ✅ Traces appear in Langfuse dashboard
- ✅ LLM calls are automatically traced
- ✅ Metadata and tags are captured
- ✅ All tests pass

## Next Steps

After PR#2A is complete and merged:

1. **PR#2B: Workflow & Communication POCs**
   - LangGraph workflow POC with Langfuse integration
   - WebSocket POC for real-time communication
   - End-to-end POC: Query → Trace → WebSocket event

2. **PR#3: Authentication & Authorization**
   - User authentication system
   - OPA integration for authorization
   - JWT token management

## References

- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [MindsDB Documentation](https://docs.mindsdb.com/)
- [Langfuse Documentation](https://langfuse.com/docs)
- [LangChain Documentation](https://python.langchain.com/docs/)

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review external service documentation
3. Verify environment configuration
4. Check service status pages

## License

This is part of the Agentic BI Platform project.
