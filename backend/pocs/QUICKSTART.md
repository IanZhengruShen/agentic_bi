# Quick Start Guide - PR#2A POCs

## 5-Minute Setup

### 1. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your actual credentials:
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_DEPLOYMENT
# - MINDSDB_API_URL
# - LANGFUSE_PUBLIC_KEY
# - LANGFUSE_SECRET_KEY
```

### 2. Install Dependencies

```bash
# From project root
pip install -e .
```

### 3. Run Combined POC

```bash
cd backend/pocs
python combined_llm_langfuse_poc.py
```

## Expected Result

```
============================================================
Combined Azure OpenAI + Langfuse Integration POC
============================================================

1. Loading configuration...
   ✓ Azure OpenAI Endpoint: https://your-resource.openai.azure.com/
   ✓ Azure Deployment: gpt-4
   ✓ Langfuse Host: https://cloud.langfuse.com

2. Testing single LLM call with Langfuse tracing...
   ✓ LLM call successful!

   Response:
   Business intelligence is the process of analyzing data...

   Trace URL: https://cloud.langfuse.com/trace/abc123

3. Testing multiple LLM calls in one trace session...
   ✓ Multiple calls successful!
   ...

============================================================
POC Status: SUCCESS
============================================================
```

## Verify in Langfuse Dashboard

1. Open the trace URL shown in the output
2. Verify you see:
   - LLM input messages
   - LLM output responses
   - Token usage metrics
   - Custom metadata and tags
   - Proper trace hierarchy

## Run Tests

```bash
cd backend
pytest tests/pocs/ -v
```

## Troubleshooting

### Missing Environment Variables

**Error:** `Missing required configuration`

**Fix:**
```bash
# Check which variables are missing
grep -E "AZURE_OPENAI|MINDSDB|LANGFUSE" .env

# Add missing values to .env file
```

### Invalid Credentials

**Error:** `Authentication failed`

**Fix:**
- Verify keys in Azure Portal / Langfuse dashboard
- Ensure no extra spaces in .env file
- Check keys are not placeholder values

### Network Issues

**Error:** `Connection refused` or `Timeout`

**Fix:**
- Verify external services are accessible
- Check firewall/proxy settings
- Test URLs in browser first

## Next Steps

After successful POC validation:

1. Review the full documentation in `README.md`
2. Explore individual POC implementations
3. Check connection patterns for your use case
4. Proceed to PR#2B: Workflow & Communication POCs
