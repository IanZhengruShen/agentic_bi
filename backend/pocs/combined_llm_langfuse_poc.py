"""
Combined Azure OpenAI + Langfuse Integration POC

This POC demonstrates the end-to-end integration:
1. Azure OpenAI LLM calls
2. Langfuse callback handler for tracing
3. Automatic trace capture of LLM operations
4. Metadata and token tracking
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langfuse.callback import CallbackHandler


def load_config() -> Dict[str, str]:
    """Load configuration from environment."""
    # Load from .env file if it exists
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    config = {
        # Azure OpenAI
        "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
        "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
        # Langfuse
        "langfuse_public_key": os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        "langfuse_secret_key": os.getenv("LANGFUSE_SECRET_KEY", ""),
        "langfuse_host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    }

    # Validate Azure OpenAI config
    azure_missing = [
        k for k in ["azure_api_key", "azure_endpoint", "azure_deployment"]
        if not config[k]
    ]
    if azure_missing:
        raise ValueError(f"Missing Azure OpenAI configuration: {', '.join(azure_missing)}")

    # Validate Langfuse config
    langfuse_missing = [
        k for k in ["langfuse_public_key", "langfuse_secret_key"]
        if not config[k] or config[k].startswith("pk-lf-xxx") or config[k].startswith("sk-lf-xxx")
    ]
    if langfuse_missing:
        raise ValueError(f"Missing or invalid Langfuse configuration: {', '.join(langfuse_missing)}")

    return config


def verify_llm_with_langfuse(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Verify Azure OpenAI LLM with Langfuse tracing.

    Returns:
        Dict containing:
        - success: bool
        - response: str (LLM response)
        - trace_url: str (Langfuse dashboard URL)
        - error: str (if any)
    """
    result: Dict[str, Any] = {
        "success": False,
        "response": None,
        "trace_url": None,
        "error": None,
    }

    try:
        # Initialize Langfuse callback handler
        langfuse_handler = CallbackHandler(
            public_key=config["langfuse_public_key"],
            secret_key=config["langfuse_secret_key"],
            host=config["langfuse_host"],
            trace_name="poc_azure_openai_call",
            user_id="poc_user",
            metadata={
                "environment": "development",
                "test_type": "combined_poc",
                "model": config["azure_deployment"],
            },
            tags=["poc", "azure-openai", "langfuse", "pr2a"],
        )

        # Initialize Azure OpenAI with LangChain
        llm = AzureChatOpenAI(
            azure_endpoint=config["azure_endpoint"],
            api_key=config["azure_api_key"],
            api_version=config["azure_api_version"],
            deployment_name=config["azure_deployment"],
            temperature=0.7,
            max_tokens=150,
        )

        # Create messages
        messages = [
            SystemMessage(content="You are a helpful AI assistant for business intelligence."),
            HumanMessage(content="Explain what business intelligence is in one sentence."),
        ]

        # Make LLM call with Langfuse tracing
        response = llm.invoke(
            messages,
            config={"callbacks": [langfuse_handler]}
        )

        # Extract response
        result["success"] = True
        result["response"] = response.content

        # Get trace URL
        if hasattr(langfuse_handler, "trace"):
            result["trace_url"] = langfuse_handler.trace.get_trace_url()

        # Flush to ensure trace is sent
        langfuse_handler.flush()

    except Exception as e:
        result["error"] = f"LLM + Langfuse error: {str(e)}"

    return result


def verify_multiple_calls_with_tracing(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Verify multiple LLM calls with a single trace session.

    Returns:
        Dict containing test results
    """
    result: Dict[str, Any] = {
        "success": False,
        "responses": [],
        "trace_url": None,
        "error": None,
    }

    try:
        # Initialize Langfuse callback handler for session
        langfuse_handler = CallbackHandler(
            public_key=config["langfuse_public_key"],
            secret_key=config["langfuse_secret_key"],
            host=config["langfuse_host"],
            trace_name="poc_multiple_calls_session",
            user_id="poc_user",
            metadata={
                "environment": "development",
                "test_type": "multi_call_poc",
                "call_count": 3,
            },
            tags=["poc", "multi-call", "pr2a"],
        )

        # Initialize Azure OpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=config["azure_endpoint"],
            api_key=config["azure_api_key"],
            api_version=config["azure_api_version"],
            deployment_name=config["azure_deployment"],
            temperature=0.7,
            max_tokens=50,
        )

        # Test queries
        queries = [
            "What is SQL?",
            "What is a database?",
            "What is data analysis?",
        ]

        # Make multiple calls
        for i, query in enumerate(queries, 1):
            messages = [
                SystemMessage(content="You are a concise technical assistant."),
                HumanMessage(content=f"{query} Answer in one short sentence."),
            ]

            response = llm.invoke(
                messages,
                config={"callbacks": [langfuse_handler]}
            )

            result["responses"].append({
                "query": query,
                "response": response.content,
            })

        result["success"] = True

        # Get trace URL
        if hasattr(langfuse_handler, "trace"):
            result["trace_url"] = langfuse_handler.trace.get_trace_url()

        # Flush to ensure trace is sent
        langfuse_handler.flush()

    except Exception as e:
        result["error"] = f"Multi-call test error: {str(e)}"

    return result


def main():
    """Run the combined Azure OpenAI + Langfuse POC."""
    print("=" * 60)
    print("Combined Azure OpenAI + Langfuse Integration POC")
    print("=" * 60)

    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config()
        print(f"   ✓ Azure OpenAI Endpoint: {config['azure_endpoint']}")
        print(f"   ✓ Azure Deployment: {config['azure_deployment']}")
        print(f"   ✓ Langfuse Host: {config['langfuse_host']}")

        # Test single LLM call with tracing
        print("\n2. Testing single LLM call with Langfuse tracing...")
        result = verify_llm_with_langfuse(config)

        if not result["success"]:
            print(f"   ✗ Test failed!")
            print(f"\nError: {result['error']}")
            print("\n" + "=" * 60)
            print("POC Status: FAILED")
            print("=" * 60)
            sys.exit(1)

        print("   ✓ LLM call successful!")
        print(f"\n   Response:")
        print(f"   {result['response']}")
        print(f"\n   Trace URL: {result['trace_url']}")

        # Test multiple calls in one session
        print("\n3. Testing multiple LLM calls in one trace session...")
        multi_result = verify_multiple_calls_with_tracing(config)

        if not multi_result["success"]:
            print(f"   ✗ Multi-call test failed!")
            print(f"\nError: {multi_result['error']}")
            print("\n" + "=" * 60)
            print("POC Status: PARTIAL SUCCESS")
            print("=" * 60)
            sys.exit(1)

        print("   ✓ Multiple calls successful!")
        for i, call in enumerate(multi_result["responses"], 1):
            print(f"\n   Call {i}: {call['query']}")
            print(f"   Response: {call['response'][:80]}...")

        print(f"\n   Session Trace URL: {multi_result['trace_url']}")

        print("\n4. Verification Steps:")
        print("   - Open Langfuse dashboard")
        print("   - Locate traces tagged with 'poc' and 'pr2a'")
        print("   - Verify LLM calls are captured with:")
        print("     • Input messages")
        print("     • Output responses")
        print("     • Token usage")
        print("     • Model metadata")
        print("     • Custom tags and metadata")

        print("\n" + "=" * 60)
        print("POC Status: SUCCESS")
        print("=" * 60)
        print("\nKey Achievements:")
        print("✓ Azure OpenAI integration working")
        print("✓ Langfuse tracing capturing LLM calls")
        print("✓ Metadata and tags properly attached")
        print("✓ Multiple calls tracked in single session")
        print("\nReady to proceed to PR#2B: Workflow & Communication POCs")

    except ValueError as e:
        print(f"   ✗ Configuration error: {e}")
        print("\n" + "=" * 60)
        print("POC Status: FAILED")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        print("\n" + "=" * 60)
        print("POC Status: FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
