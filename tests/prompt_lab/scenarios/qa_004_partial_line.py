"""QA-004: partial-line — Prompt without trailing newline is still detected."""

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
class PartialLineScenario(LabScenario):
    scenario_id = "QA-004"
    name = "partial-line-prompt"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        # Prompt without trailing newline — real PTY behaviour
        await pty.write(b"Delete all files? [y/N]")  # no \n

    def assert_results(self, results: ScenarioResults) -> None:
        assert len(results.prompt_events) >= 1, "Expected prompt event for partial-line prompt"
        event = results.prompt_events[0]
        assert event.prompt_type == PromptType.TYPE_YES_NO, (
            f"Expected YES_NO for partial-line, got {event.prompt_type}"
        )
