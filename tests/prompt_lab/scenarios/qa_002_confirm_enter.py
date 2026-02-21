"""QA-002: confirm-enter — Press Enter detection."""

from __future__ import annotations

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from aegis.core.prompt.models import PromptType


@ScenarioRegistry.register
class ConfirmEnterScenario(LabScenario):
    scenario_id = "QA-002"
    name = "confirm-enter"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        await pty.write(b"Press Enter to continue")

    def assert_results(self, results: ScenarioResults) -> None:
        assert len(results.prompt_events) >= 1, "Expected at least one prompt event"
        event = results.prompt_events[0]
        assert event.prompt_type == PromptType.TYPE_CONFIRM_ENTER, (
            f"Expected CONFIRM_ENTER, got {event.prompt_type}"
        )
