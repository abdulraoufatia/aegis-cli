"""QA-007: echo-suppression — No re-detection immediately after injection."""

from __future__ import annotations

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from atlasbridge.core.prompt.detector import PromptDetector


@ScenarioRegistry.register
class EchoSuppressionScenario(LabScenario):
    scenario_id = "QA-007"
    name = "echo-suppression"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        # Simulate inject → echo of injected text → should not re-detect
        d = PromptDetector(session_id="qa-007")
        d.mark_injected()
        # Immediately after injection, even a YES_NO prompt should be suppressed
        event = d.analyse(b"Overwrite? [y/N] ")
        assert event is None, "Detection should be suppressed immediately after injection"

    def assert_results(self, results: ScenarioResults) -> None:
        assert results.error == "", f"Scenario error: {results.error}"
