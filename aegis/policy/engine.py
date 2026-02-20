"""
Aegis policy engine — decides what to do with a detected prompt.

For v0.x the engine is intentionally simple:
  - All prompts are routed to the user via Telegram (ROUTE_TO_USER).
  - No plaintext TOML rules are evaluated yet (future roadmap).
  - The only hard-coded deny: prompts that exceed the queue limit.

The engine is synchronous; the async bridge calls it before creating a DB
record or sending a Telegram message.
"""

from __future__ import annotations

from dataclasses import dataclass

from aegis.core.constants import PolicyAction, PromptType
from aegis.policy.detector import DetectionResult


@dataclass
class PolicyDecision:
    action: PolicyAction
    reason: str
    # If AUTO_INJECT, the value to inject
    inject_value: str | None = None


class PolicyEngine:
    """
    Evaluate a DetectionResult and return a PolicyDecision.

    Parameters
    ----------
    free_text_enabled:
        Whether TYPE_FREE_TEXT prompts are forwarded to the user.
        If False, they fall back to the safe default (empty string).
    """

    def __init__(self, free_text_enabled: bool = False) -> None:
        self.free_text_enabled = free_text_enabled

    def evaluate(self, result: DetectionResult) -> PolicyDecision:
        """Return a PolicyDecision for a detected prompt."""

        # TYPE_FREE_TEXT: only route if explicitly enabled
        if result.prompt_type == PromptType.FREE_TEXT and not self.free_text_enabled:
            return PolicyDecision(
                action=PolicyAction.AUTO_INJECT,
                reason="free_text disabled in config; using safe default",
                inject_value="",
            )

        # All other detected prompts go to the user
        return PolicyDecision(
            action=PolicyAction.ROUTE_TO_USER,
            reason="default policy: route all prompts to user",
        )
