"""
Workflows module for multi-agent coordination.

This module provides unified workflow orchestration for coordinating
multiple agents (AnalysisAgent, VisualizationAgent, etc.) using LangGraph.

Key Components:
- UnifiedWorkflowState: State management across multiple agents
- UnifiedWorkflowOrchestrator: LangGraph-based workflow orchestration
- Coordination nodes: Adapter nodes that invoke agent subgraphs
- Error recovery: Resilient error handling strategies
"""

from app.workflows.unified_state import UnifiedWorkflowState
from app.workflows.orchestrator import UnifiedWorkflowOrchestrator, create_unified_orchestrator

__all__ = [
    "UnifiedWorkflowState",
    "UnifiedWorkflowOrchestrator",
    "create_unified_orchestrator",
]
