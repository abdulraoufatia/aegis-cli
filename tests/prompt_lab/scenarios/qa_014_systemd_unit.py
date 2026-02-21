"""QA-014: systemd-unit — Generated unit file contains required sections."""

from __future__ import annotations

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from atlasbridge.os.systemd.service import generate_unit_file


@ScenarioRegistry.register
class SystemdUnitScenario(LabScenario):
    scenario_id = "QA-014"
    name = "systemd-unit"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        unit = generate_unit_file(
            exec_path="/usr/local/bin/atlasbridge",
            config_path="/home/user/.config/atlasbridge/config.toml",
        )

        # Required sections
        assert "[Unit]" in unit, "Missing [Unit] section"
        assert "[Service]" in unit, "Missing [Service] section"
        assert "[Install]" in unit, "Missing [Install] section"

        # Required directives
        assert "ExecStart=/usr/local/bin/atlasbridge" in unit, "ExecStart must reference exec_path"
        assert "ATLASBRIDGE_CONFIG=/home/user/.config/atlasbridge/config.toml" in unit, (
            "Environment must set ATLASBRIDGE_CONFIG"
        )
        assert "Restart=on-failure" in unit, "Service must restart on failure"
        assert "WantedBy=default.target" in unit, "Service must be enabled for user sessions"

        # Must not contain unresolved template placeholders
        assert "{exec_path}" not in unit, "Template placeholder {exec_path} not substituted"
        assert "{config_path}" not in unit, "Template placeholder {config_path} not substituted"

    def assert_results(self, results: ScenarioResults) -> None:
        assert results.error == "", f"Scenario error: {results.error}"
