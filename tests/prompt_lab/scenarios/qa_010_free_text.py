"""QA-010: free-text — Free text prompt detection."""

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
class FreeTextScenario(LabScenario):
    scenario_id = "QA-010"
    name = "free-text"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        await pty.write(b"Enter your API key:")

    def assert_results(self, results: ScenarioResults) -> None:
        assert len(results.prompt_events) >= 1, "Expected at least one prompt event"
        event = results.prompt_events[0]
        assert event.prompt_type == PromptType.TYPE_FREE_TEXT, (
            f"Expected FREE_TEXT, got {event.prompt_type}"
        )
