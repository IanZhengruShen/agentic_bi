"""
LangGraph Workflow POC with Langfuse Integration

This POC demonstrates:
1. Basic LangGraph workflow with state management
2. Multi-step agent workflow
3. Langfuse tracing for entire workflow
4. State transitions and conditional routing
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, TypedDict, Annotated, Literal
import operator

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langfuse.callback import CallbackHandler


# Define workflow state
class WorkflowState(TypedDict):
    """State that gets passed between workflow nodes."""
    query: str
    intent: str
    sql_query: str
    result: str
    error: str
    messages: Annotated[list, operator.add]


def load_config() -> Dict[str, str]:
    """Load configuration from environment."""
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

    # Validate
    azure_missing = [k for k in ["azure_api_key", "azure_endpoint"] if not config[k]]
    if azure_missing:
        raise ValueError(f"Missing Azure OpenAI configuration: {', '.join(azure_missing)}")

    langfuse_missing = [
        k for k in ["langfuse_public_key", "langfuse_secret_key"]
        if not config[k] or config[k].startswith("pk-lf-xxx") or config[k].startswith("sk-lf-xxx")
    ]
    if langfuse_missing:
        raise ValueError(f"Missing or invalid Langfuse configuration: {', '.join(langfuse_missing)}")

    return config


def create_workflow(config: Dict[str, str], langfuse_handler: CallbackHandler) -> StateGraph:
    """
    Create a simple LangGraph workflow for query processing.

    Workflow steps:
    1. classify_intent: Determine what the user wants to do
    2. generate_sql: Create SQL query based on intent
    3. format_response: Format the final response
    """

    # Initialize LLM
    llm = AzureChatOpenAI(
        azure_endpoint=config["azure_endpoint"],
        api_key=config["azure_api_key"],
        api_version=config["azure_api_version"],
        deployment_name=config["azure_deployment"],
        temperature=0.7,
        max_tokens=200,
    )

    # Node 1: Classify Intent
    def classify_intent(state: WorkflowState) -> WorkflowState:
        """Classify the user's intent."""
        messages = [
            SystemMessage(content="You are a helpful assistant that classifies user queries. "
                                "Respond with only one word: 'analytics', 'reporting', or 'exploration'."),
            HumanMessage(content=f"Classify this query: {state['query']}")
        ]

        response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
        intent = response.content.strip().lower()

        return {
            **state,
            "intent": intent,
            "messages": [f"Intent classified as: {intent}"]
        }

    # Node 2: Generate SQL
    def generate_sql(state: WorkflowState) -> WorkflowState:
        """Generate SQL based on intent and query."""
        messages = [
            SystemMessage(content=f"You are a SQL expert. Generate a simple SQL query for {state['intent']} purposes. "
                                "Keep it simple and educational. Just return the SQL query, no explanation."),
            HumanMessage(content=state['query'])
        ]

        response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
        sql = response.content.strip()

        return {
            **state,
            "sql_query": sql,
            "messages": [f"Generated SQL query"]
        }

    # Node 3: Format Response
    def format_response(state: WorkflowState) -> WorkflowState:
        """Format the final response."""
        result = f"""
Query: {state['query']}
Intent: {state['intent']}
SQL: {state['sql_query']}

Workflow completed successfully!
"""
        return {
            **state,
            "result": result.strip(),
            "messages": ["Response formatted"]
        }

    # Create workflow graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("format_response", format_response)

    # Define edges (simple linear flow for POC)
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "generate_sql")
    workflow.add_edge("generate_sql", "format_response")
    workflow.add_edge("format_response", END)

    return workflow


def run_workflow_poc(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Run the LangGraph workflow POC with Langfuse tracing.

    Returns:
        Dict containing:
        - success: bool
        - result: final workflow output
        - trace_url: Langfuse dashboard URL
        - error: str (if any)
    """
    result: Dict[str, Any] = {
        "success": False,
        "result": None,
        "trace_url": None,
        "error": None,
    }

    try:
        # Initialize Langfuse callback handler
        langfuse_handler = CallbackHandler(
            public_key=config["langfuse_public_key"],
            secret_key=config["langfuse_secret_key"],
            host=config["langfuse_host"],
            trace_name="poc_langgraph_workflow",
            user_id="poc_user",
        )

        # Create and compile workflow
        workflow = create_workflow(config, langfuse_handler)
        app = workflow.compile()

        # Run workflow with a test query
        initial_state: WorkflowState = {
            "query": "Show me the total sales for last quarter",
            "intent": "",
            "sql_query": "",
            "result": "",
            "error": "",
            "messages": [],
        }

        final_state = app.invoke(initial_state)

        result["success"] = True
        result["result"] = final_state

        # Get trace URL
        if hasattr(langfuse_handler, 'trace'):
            result["trace_url"] = langfuse_handler.trace.get_trace_url()

        # Flush to ensure trace is sent
        langfuse_handler.flush()

    except Exception as e:
        result["error"] = f"Workflow error: {str(e)}"

    return result


def main():
    """Run the LangGraph workflow POC."""
    print("=" * 60)
    print("LangGraph Workflow POC with Langfuse Integration")
    print("=" * 60)

    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config()
        print(f"   ✓ Azure OpenAI Endpoint: {config['azure_endpoint']}")
        print(f"   ✓ Langfuse Host: {config['langfuse_host']}")

        # Run workflow
        print("\n2. Running LangGraph workflow...")
        result = run_workflow_poc(config)

        if not result["success"]:
            print(f"   ✗ Workflow failed!")
            print(f"\nError: {result['error']}")
            print("\n" + "=" * 60)
            print("POC Status: FAILED")
            print("=" * 60)
            sys.exit(1)

        print("   ✓ Workflow executed successfully!")

        # Display results
        print("\n3. Workflow Results:")
        final_state = result["result"]
        print(f"   Query: {final_state.get('query')}")
        print(f"   Intent: {final_state.get('intent')}")
        print(f"   SQL Generated: {final_state.get('sql_query')[:80]}...")
        print(f"   Messages: {len(final_state.get('messages', []))} steps")

        print(f"\n4. Langfuse Trace:")
        print(f"   {result['trace_url']}")

        print("\n5. Verification Steps:")
        print("   - Open Langfuse dashboard")
        print("   - Look for trace: 'poc_langgraph_workflow'")
        print("   - Verify workflow steps are captured:")
        print("     • classify_intent")
        print("     • generate_sql")
        print("     • format_response")
        print("   - Check that all LLM calls are traced")
        print("   - Verify state transitions are visible")

        print("\n" + "=" * 60)
        print("POC Status: SUCCESS")
        print("=" * 60)
        print("\nKey Achievements:")
        print("✓ LangGraph workflow created")
        print("✓ Multi-step agent flow working")
        print("✓ Langfuse tracing entire workflow")
        print("✓ State transitions tracked")
        print("\nReady for WebSocket POC!")

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
