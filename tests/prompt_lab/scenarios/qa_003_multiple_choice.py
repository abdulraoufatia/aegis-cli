"""QA-003: multiple-choice — Numbered list prompt detection."""

from __future__ import annotations

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from atlasbridge.core.prompt.models import PromptType


@ScenarioRegistry.register
class MultipleChoiceScenario(LabScenario):
    scenario_id = "QA-003"
    name = "multiple-choice"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        await pty.write(b"Choose an option:\n1) Install\n2) Update\n3) Remove\n")

    def assert_results(self, results: ScenarioResults) -> None:
        assert len(results.prompt_events) >= 1, "Expected at least one prompt event"
        event = results.prompt_events[0]
        assert event.prompt_type == PromptType.TYPE_MULTIPLE_CHOICE, (
            f"Expected MULTIPLE_CHOICE, got {event.prompt_type}"
        )
