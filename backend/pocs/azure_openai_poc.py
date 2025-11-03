"""
Azure OpenAI Integration POC

This POC demonstrates:
1. Basic connection to Azure OpenAI
2. Simple completion test
3. Token usage tracking
4. Error handling
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import AzureOpenAI
from openai import OpenAIError


def load_config() -> Dict[str, str]:
    """Load Azure OpenAI configuration from environment."""
    # Load from .env file if it exists
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    config = {
        "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
    }

    # Validate configuration
    missing = [k for k, v in config.items() if not v]
    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    return config


def verify_azure_openai_connection(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Verify Azure OpenAI connection with a simple completion.

    Returns:
        Dict containing:
        - success: bool
        - response: str (completion text)
        - tokens: dict (usage statistics)
        - error: str (if any)
    """
    result: Dict[str, Any] = {
        "success": False,
        "response": None,
        "tokens": None,
        "error": None,
    }

    try:
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            api_key=config["api_key"],
            api_version=config["api_version"],
            azure_endpoint=config["endpoint"],
        )

        # Test with a simple prompt
        response = client.chat.completions.create(
            model=config["deployment"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello from Azure OpenAI!' in exactly 5 words."}
            ],
            max_tokens=50,
            temperature=0.7,
        )

        # Extract response data
        result["success"] = True
        result["response"] = response.choices[0].message.content
        result["tokens"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    except OpenAIError as e:
        result["error"] = f"OpenAI API Error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected Error: {str(e)}"

    return result


def main():
    """Run the Azure OpenAI POC."""
    print("=" * 60)
    print("Azure OpenAI Integration POC")
    print("=" * 60)

    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config()
        print(f"   ✓ Endpoint: {config['endpoint']}")
        print(f"   ✓ Deployment: {config['deployment']}")
        print(f"   ✓ API Version: {config['api_version']}")

        # Test connection
        print("\n2. Testing Azure OpenAI connection...")
        result = verify_azure_openai_connection(config)

        if result["success"]:
            print("   ✓ Connection successful!")
            print(f"\n3. Response:")
            print(f"   {result['response']}")
            print(f"\n4. Token Usage:")
            print(f"   - Prompt tokens: {result['tokens']['prompt_tokens']}")
            print(f"   - Completion tokens: {result['tokens']['completion_tokens']}")
            print(f"   - Total tokens: {result['tokens']['total_tokens']}")
            print("\n" + "=" * 60)
            print("POC Status: SUCCESS")
            print("=" * 60)
        else:
            print(f"   ✗ Connection failed!")
            print(f"\nError: {result['error']}")
            print("\n" + "=" * 60)
            print("POC Status: FAILED")
            print("=" * 60)
            sys.exit(1)

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
