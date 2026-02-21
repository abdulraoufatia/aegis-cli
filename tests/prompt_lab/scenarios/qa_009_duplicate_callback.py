"""QA-009: duplicate-callback — Second tap with same nonce is rejected."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.prompt_lab.simulator import (
    LabScenario,
    PTYSimulator,
    ScenarioRegistry,
    ScenarioResults,
    TelegramStub,
)
from atlasbridge.core.store.database import Database


@ScenarioRegistry.register
class DuplicateCallbackScenario(LabScenario):
    scenario_id = "QA-009"
    name = "duplicate-callback"

    async def setup(self, pty: PTYSimulator, stub: TelegramStub) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "qa009.db"
            db = Database(db_path)
            db.connect()
            try:
                sid = str(uuid.uuid4())
                pid = str(uuid.uuid4())
                nonce = secrets.token_hex(16)
                expires_at = (datetime.now(UTC) + timedelta(seconds=600)).isoformat()

                db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
                db.save_prompt(
                    prompt_id=pid,
                    session_id=sid,
                    prompt_type="yes_no",
                    confidence="high",
                    excerpt="Continue?",
                    nonce=nonce,
                    expires_at=expires_at,
                )

                # First tap — should succeed
                rows1 = db.decide_prompt(pid, "reply_received", "telegram:1", "y", nonce)
                assert rows1 == 1, f"First decide_prompt should succeed, got rowcount={rows1}"

                # Second tap — same nonce, must be rejected
                rows2 = db.decide_prompt(pid, "reply_received", "telegram:1", "n", nonce)
                assert rows2 == 0, (
                    f"Duplicate decide_prompt must be rejected (nonce_used=1), got rowcount={rows2}"
                )
            finally:
                db.close()

    def assert_results(self, results: ScenarioResults) -> None:
        assert results.error == "", f"Scenario error: {results.error}"
