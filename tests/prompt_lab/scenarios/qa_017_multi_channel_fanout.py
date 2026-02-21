"""QA-017: multi-channel-fanout — MultiChannel broadcasts prompt to all sub-channels."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from atlasbridge.channels.multi import MultiChannel
from atlasbridge.core.prompt.models import PromptEvent, PromptType


@ScenarioRegistry.register
class MultiChannelFanoutScenario(LabScenario):
    scenario_id = "QA-017"
    name = "multi-channel-fanout"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        await pty.write(b"Deploy to production? [y/n] ")

    def assert_results(self, results: ScenarioResults) -> None:
        assert len(results.prompt_events) >= 1, "Expected a YES/NO prompt event"
        event = results.prompt_events[0]
        assert event.prompt_type == PromptType.TYPE_YES_NO

        # Verify MultiChannel fan-out behaviour synchronously
        ch1 = MagicMock()
        ch1.channel_name = "telegram"
        ch1.send_prompt = AsyncMock(return_value="12345")
        ch2 = MagicMock()
        ch2.channel_name = "slack"
        ch2.send_prompt = AsyncMock(return_value="D12345:1234567890.123456")

        multi = MultiChannel([ch1, ch2])

        result = asyncio.get_event_loop().run_until_complete(multi.send_prompt(event))
        # Both channels received the prompt
        ch1.send_prompt.assert_called_once_with(event)
        ch2.send_prompt.assert_called_once_with(event)
        # First channel result is returned, prefixed with channel name
        assert result == "telegram:12345"
