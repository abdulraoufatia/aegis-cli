"""QA-008: ttl-expiry — Prompt state machine expires correctly."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from atlasbridge.core.prompt.models import Confidence, PromptEvent, PromptStatus, PromptType
from atlasbridge.core.prompt.state import PromptStateMachine


@ScenarioRegistry.register
class TTLExpiryScenario(LabScenario):
    scenario_id = "QA-008"
    name = "ttl-expiry"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        event = PromptEvent.create(
            session_id="qa-008",
            prompt_type=PromptType.TYPE_YES_NO,
            confidence=Confidence.HIGH,
            excerpt="Expired prompt",
            ttl_seconds=1,
        )
        sm = PromptStateMachine(event=event)
        sm.transition(PromptStatus.ROUTED)
        sm.transition(PromptStatus.AWAITING_REPLY)

        # Force TTL into the past
        sm.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)

        expired = sm.expire_if_due()
        assert expired, "expire_if_due() should return True for overdue prompt"
        assert sm.status == PromptStatus.EXPIRED, f"Expected EXPIRED, got {sm.status}"
        # Terminal — no further injections possible
        assert sm.is_terminal

    def assert_results(self, results: ScenarioResults) -> None:
        assert results.error == "", f"Scenario error: {results.error}"
