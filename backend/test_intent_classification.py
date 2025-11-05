"""
Quick test script for intent classification functionality.

This tests the new intent identification feature that routes queries
based on whether they are data analysis related or not.
"""

import asyncio
import sys
from app.agents.analysis_agent_langgraph import create_analysis_agent


async def test_intent_classification():
    """Test intent classification with various queries."""

    # Create agent
    agent = create_analysis_agent(enable_checkpointing=False)

    # Test queries
    test_cases = [
        {
            "query": "Show me total sales for last month",
            "expected": "DATA_ANALYSIS",
            "description": "Data analysis query - should route to SQL generation"
        },
        {
            "query": "Hello, how are you?",
            "expected": "OTHER",
            "description": "Greeting - should be handled as non-analysis"
        },
        {
            "query": "What's the weather today?",
            "expected": "OTHER",
            "description": "General question - should be handled as non-analysis"
        },
        {
            "query": "Compare revenue between Q1 and Q2",
            "expected": "DATA_ANALYSIS",
            "description": "Data comparison - should route to SQL generation"
        },
        {
            "query": "Tell me a joke",
            "expected": "OTHER",
            "description": "Entertainment request - should be handled as non-analysis"
        },
        {
            "query": "List all customers from California",
            "expected": "DATA_ANALYSIS",
            "description": "Data retrieval - should route to SQL generation"
        },
    ]

    print("=" * 80)
    print("Testing Intent Classification")
    print("=" * 80)

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        description = test_case["description"]

        print(f"\nTest {i}/{len(test_cases)}: {description}")
        print(f"Query: '{query}'")
        print(f"Expected: {expected}")

        try:
            # Execute workflow
            result = await agent.execute(
                query=query,
                database="test_db",
                user_id="test_user",
            )

            # Check intent classification
            actual_intent = result.get("query_intent", "UNKNOWN")
            confidence = result.get("intent_confidence", 0.0)
            reasoning = result.get("intent_reasoning", "")
            intent_rejection = result.get("intent_rejection", False)
            final_message = result.get("final_message", "")

            print(f"Actual: {actual_intent} (confidence: {confidence:.2f})")
            print(f"Reasoning: {reasoning}")

            if intent_rejection:
                print(f"✓ Query was handled as non-analysis")
                print(f"Response: {final_message[:200]}...")
            else:
                print(f"✓ Query was routed to data analysis workflow")

            # Check if classification matches expectation
            if actual_intent == expected:
                print("✅ PASSED")
                passed += 1
            else:
                print(f"❌ FAILED: Expected {expected}, got {actual_intent}")
                failed += 1

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    # Cleanup
    await agent.cleanup()

    return passed, failed


if __name__ == "__main__":
    # Run tests
    passed, failed = asyncio.run(test_intent_classification())

    # Exit with error code if any tests failed
    sys.exit(0 if failed == 0 else 1)
