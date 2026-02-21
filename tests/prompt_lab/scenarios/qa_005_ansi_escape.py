"""QA-005: ansi-escape — ANSI codes stripped before detection."""

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
class AnsiEscapeScenario(LabScenario):
    scenario_id = "QA-005"
    name = "ansi-escape"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        # Prompt wrapped in ANSI colour codes — detector must strip them first
        await pty.write(b"\x1b[1;33mOverwrite existing file?\x1b[0m (yes/no) ")

    def assert_results(self, results: ScenarioResults) -> None:
        assert len(results.prompt_events) >= 1, "Expected prompt event even with ANSI escape codes"
        event = results.prompt_events[0]
        assert event.prompt_type == PromptType.TYPE_YES_NO, (
            f"Expected YES_NO after ANSI strip, got {event.prompt_type}"
        )
