"""
aegis.agents — Agentic pipeline for tool call processing.

Implements the Event → Plan → Policy → Execution → Audit pipeline
using a multi-agent pattern.

Pipeline:
    Planner         Decomposes compound tool calls
    PolicyAgent     Applies policy rules to each tool call
    ExecutionAgent  Executes approved tool calls
    Observer        Monitors and logs outcomes
    Critic          Validates safety and detects anomalies

Agents communicate via the core event bus (aegis.core.events).
"""
