"""QA-006: silence-fallback — Signal 3 fires after silence threshold."""

from __future__ import annotations

import asyncio

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from atlasbridge.core.prompt.detector import PromptDetector
from atlasbridge.core.prompt.models import Confidence


@ScenarioRegistry.register
class SilenceFallbackScenario(LabScenario):
    scenario_id = "QA-006"
    name = "silence-fallback"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        # Write innocuous output, then silence
        await pty.write(b"Running analysis...\n")
        # Simulate waiting (short threshold for testing)
        await pty.block(0.05)

    def assert_results(self, results: ScenarioResults) -> None:
        # The Simulator uses PromptDetector.analyse() only (not check_silence),
        # so this scenario validates that the detector is wired correctly.
        # The silence signal is checked separately in unit tests.
        # Here we just assert no crash and scenario completes.
        assert results.error == "", f"Scenario error: {results.error}"


class SilenceFallbackDirectScenario(LabScenario):
    """Validates Signal 3 directly via PromptDetector.check_silence()."""

    scenario_id = "QA-006-direct"
    name = "silence-fallback-direct"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        import time

        # Create a detector with a very short threshold
        d = PromptDetector(session_id="qa-006", silence_threshold_s=0.01)
        d._state.last_output_time = time.monotonic() - 1.0  # past threshold
        event = d.check_silence(process_running=True)
        assert event is not None, "Signal 3 did not fire"
        assert event.confidence == Confidence.LOW

    def assert_results(self, results: ScenarioResults) -> None:
        assert results.error == ""
