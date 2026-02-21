"""QA-001: yes-no-prompt — y/n detection and Telegram button response."""

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
class YesNoPromptScenario(LabScenario):
    scenario_id = "QA-001"
    name = "yes-no-prompt"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        stub.auto_reply("Yes")
        await pty.write(b"Do you want to continue? [y/N] ")

    def assert_results(self, results: ScenarioResults) -> None:
        assert len(results.prompt_events) >= 1, "Expected at least one prompt event"
        event = results.prompt_events[0]
        assert event.prompt_type == PromptType.TYPE_YES_NO, (
            f"Expected YES_NO, got {event.prompt_type}"
        )
