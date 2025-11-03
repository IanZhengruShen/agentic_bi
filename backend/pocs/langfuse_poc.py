"""
Langfuse Integration POC

This POC demonstrates:
1. Langfuse callback handler setup
2. Basic trace capture
3. Dashboard verification
4. Metadata and tags
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.callback import CallbackHandler


def load_config() -> Dict[str, str]:
    """Load Langfuse configuration from environment."""
    # Load from .env file if it exists
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    config = {
        "public_key": os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        "secret_key": os.getenv("LANGFUSE_SECRET_KEY", ""),
        "host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    }

    # Validate configuration
    missing = [k for k, v in config.items() if not v or v.startswith("pk-lf-xxx") or v.startswith("sk-lf-xxx")]
    if missing:
        raise ValueError(f"Missing or invalid configuration: {', '.join(missing)}")

    return config


def verify_langfuse_connection(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Verify Langfuse connection and basic operations.

    Returns:
        Dict containing:
        - success: bool
        - trace_url: str (Langfuse dashboard URL)
        - error: str (if any)
    """
    result: Dict[str, Any] = {
        "success": False,
        "trace_url": None,
        "error": None,
    }

    try:
        # Initialize Langfuse client
        langfuse = Langfuse(
            public_key=config["public_key"],
            secret_key=config["secret_key"],
            host=config["host"],
        )

        # Test 1: Create a simple trace
        trace = langfuse.trace(
            name="poc_test_trace",
            user_id="poc_user",
            metadata={
                "environment": "development",
                "test_type": "poc",
                "version": "0.1.0",
            },
            tags=["poc", "integration-test", "pr2a"],
        )

        # Test 2: Add a generation span
        generation = trace.generation(
            name="test_generation",
            model="test-model",
            model_parameters={
                "temperature": 0.7,
                "max_tokens": 100,
            },
            input="This is a test input for POC",
            output="This is a test output for POC",
            metadata={
                "test": True,
                "poc_stage": "initial",
            },
        )

        # Test 3: Add an event
        trace.event(
            name="poc_checkpoint",
            metadata={
                "checkpoint": "langfuse_integration_complete",
                "status": "success",
            },
        )

        # Flush to ensure data is sent
        langfuse.flush()

        result["success"] = True
        result["trace_url"] = trace.get_trace_url()

    except Exception as e:
        result["error"] = f"Langfuse error: {str(e)}"

    return result


def verify_callback_handler(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Verify Langfuse callback handler for LangChain integration.

    Returns:
        Dict containing test results
    """
    result: Dict[str, Any] = {
        "success": False,
        "handler_created": False,
        "trace_url": None,
        "error": None,
    }

    try:
        # Create callback handler
        handler = CallbackHandler(
            public_key=config["public_key"],
            secret_key=config["secret_key"],
            host=config["host"],
            trace_name="poc_callback_test",
            user_id="poc_user",
            metadata={
                "test": "callback_handler",
                "environment": "development",
            },
            tags=["poc", "callback-handler", "pr2a"],
        )

        result["handler_created"] = True

        # Get trace information
        if hasattr(handler, "trace"):
            result["trace_url"] = handler.trace.get_trace_url()

        # Flush handler
        handler.flush()

        result["success"] = True

    except Exception as e:
        result["error"] = f"Callback handler error: {str(e)}"

    return result


def main():
    """Run the Langfuse POC."""
    print("=" * 60)
    print("Langfuse Integration POC")
    print("=" * 60)

    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config()
        print(f"   ✓ Langfuse Host: {config['host']}")
        print(f"   ✓ Public Key: {config['public_key'][:10]}...")

        # Test direct Langfuse connection
        print("\n2. Testing Langfuse direct client...")
        result = verify_langfuse_connection(config)

        if not result["success"]:
            print(f"   ✗ Connection failed!")
            print(f"\nError: {result['error']}")
            print("\n" + "=" * 60)
            print("POC Status: FAILED")
            print("=" * 60)
            sys.exit(1)

        print("   ✓ Trace created successfully!")
        print(f"   ✓ Trace URL: {result['trace_url']}")

        # Test callback handler
        print("\n3. Testing Langfuse callback handler...")
        callback_result = verify_callback_handler(config)

        if not callback_result["success"]:
            print(f"   ✗ Callback handler test failed!")
            print(f"\nError: {callback_result['error']}")
            print("\n" + "=" * 60)
            print("POC Status: PARTIAL SUCCESS")
            print("=" * 60)
            sys.exit(1)

        print("   ✓ Callback handler created successfully!")
        if callback_result["trace_url"]:
            print(f"   ✓ Callback trace URL: {callback_result['trace_url']}")

        print("\n4. Verification Steps:")
        print("   - Open Langfuse dashboard at:", config['host'])
        print("   - Look for traces tagged with 'poc' and 'pr2a'")
        print("   - Verify metadata and tags are captured")
        print("   - Check trace hierarchy and spans")

        print("\n" + "=" * 60)
        print("POC Status: SUCCESS")
        print("=" * 60)
        print("\nNext Steps:")
        print("- Verify traces in Langfuse dashboard")
        print("- Check that all metadata and tags are visible")
        print("- Proceed to combined LLM + Langfuse POC")

    except ValueError as e:
        print(f"   ✗ Configuration error: {e}")
        print("\n" + "=" * 60)
        print("POC Status: FAILED")
        print("=" * 60)
        print("\nNote: Ensure LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
        print("      are set in your .env file with valid values.")
        sys.exit(1)
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        print("\n" + "=" * 60)
        print("POC Status: FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
