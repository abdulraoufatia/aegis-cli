"""Tests for SystemHealth enum, compute_health(), and display helpers."""

from __future__ import annotations

import inspect

from atlasbridge.console.app import ConsoleApp, ConsoleScreen
from atlasbridge.console.supervisor import ProcessInfo, SystemHealth, compute_health

# ---------------------------------------------------------------------------
# SystemHealth enum
# ---------------------------------------------------------------------------


class TestSystemHealthEnum:
    def test_enum_values(self):
        assert SystemHealth.GREEN.value == "green"
        assert SystemHealth.YELLOW.value == "yellow"
        assert SystemHealth.RED.value == "red"


# ---------------------------------------------------------------------------
# compute_health — process-only scenarios
# ---------------------------------------------------------------------------


class TestComputeHealthProcesses:
    def test_all_running_no_doctor(self):
        statuses = [
            ProcessInfo(name="daemon", running=True, pid=100),
            ProcessInfo(name="dashboard", running=True, pid=101),
            ProcessInfo(name="agent", running=True, pid=102),
        ]
        assert compute_health(statuses) == SystemHealth.GREEN

    def test_nothing_running(self):
        statuses = [
            ProcessInfo(name="daemon", running=False),
            ProcessInfo(name="dashboard", running=False),
            ProcessInfo(name="agent", running=False),
        ]
        assert compute_health(statuses) == SystemHealth.YELLOW

    def test_daemon_down_agent_running(self):
        statuses = [
            ProcessInfo(name="daemon", running=False),
            ProcessInfo(name="dashboard", running=False),
            ProcessInfo(name="agent", running=True, pid=102),
        ]
        assert compute_health(statuses) == SystemHealth.RED

    def test_empty_statuses(self):
        assert compute_health([]) == SystemHealth.YELLOW

    def test_daemon_only_running(self):
        statuses = [
            ProcessInfo(name="daemon", running=True, pid=100),
            ProcessInfo(name="dashboard", running=False),
            ProcessInfo(name="agent", running=False),
        ]
        assert compute_health(statuses) == SystemHealth.GREEN


# ---------------------------------------------------------------------------
# compute_health — with doctor checks
# ---------------------------------------------------------------------------


class TestComputeHealthDoctor:
    def test_doctor_fail_returns_red(self):
        statuses = [ProcessInfo(name="daemon", running=True, pid=100)]
        checks = [{"name": "config", "status": "fail"}]
        assert compute_health(statuses, doctor_checks=checks) == SystemHealth.RED

    def test_doctor_warn_returns_yellow(self):
        statuses = [ProcessInfo(name="daemon", running=True, pid=100)]
        checks = [{"name": "config", "status": "warn"}]
        assert compute_health(statuses, doctor_checks=checks) == SystemHealth.YELLOW

    def test_all_running_with_passing_doctor(self):
        statuses = [
            ProcessInfo(name="daemon", running=True, pid=100),
            ProcessInfo(name="agent", running=True, pid=101),
        ]
        checks = [
            {"name": "config", "status": "pass"},
            {"name": "database", "status": "pass"},
        ]
        assert compute_health(statuses, doctor_checks=checks) == SystemHealth.GREEN

    def test_doctor_fail_overrides_running(self):
        """Doctor failure is RED even when all processes are running."""
        statuses = [
            ProcessInfo(name="daemon", running=True, pid=100),
            ProcessInfo(name="dashboard", running=True, pid=101),
            ProcessInfo(name="agent", running=True, pid=102),
        ]
        checks = [{"name": "db", "status": "fail"}]
        assert compute_health(statuses, doctor_checks=checks) == SystemHealth.RED


# ---------------------------------------------------------------------------
# Console compose — new widget IDs
# ---------------------------------------------------------------------------


class TestConsoleComposeWidgets:
    def test_health_state_in_compose(self):
        """health-state widget ID must exist in compose."""
        source = inspect.getsource(ConsoleScreen.compose)
        assert "health-state" in source

    def test_data_paths_in_compose(self):
        """data-paths widget ID must exist in compose."""
        source = inspect.getsource(ConsoleScreen.compose)
        assert "data-paths" in source


# ---------------------------------------------------------------------------
# Audit severity mapping
# ---------------------------------------------------------------------------


class TestAuditSeverity:
    def test_expired_is_warn(self):
        assert ConsoleScreen._audit_severity("prompt_expired") == "WARN"

    def test_failed_is_warn(self):
        assert ConsoleScreen._audit_severity("inject_failed") == "WARN"

    def test_error_is_warn(self):
        assert ConsoleScreen._audit_severity("connection_error") == "WARN"

    def test_normal_is_info(self):
        assert ConsoleScreen._audit_severity("prompt_detected") == "INFO"

    def test_empty_is_info(self):
        assert ConsoleScreen._audit_severity("") == "INFO"


# ---------------------------------------------------------------------------
# Doctor icon formatting
# ---------------------------------------------------------------------------


class TestDoctorIcon:
    def test_ok_shows_pass(self):
        assert "PASS" in ConsoleScreen._doctor_icon("ok")

    def test_pass_shows_pass(self):
        assert "PASS" in ConsoleScreen._doctor_icon("pass")

    def test_warn_shows_warn(self):
        assert "WARN" in ConsoleScreen._doctor_icon("warn")

    def test_fail_shows_fail(self):
        assert "FAIL" in ConsoleScreen._doctor_icon("fail")

    def test_unknown_shows_skip(self):
        assert "SKIP" in ConsoleScreen._doctor_icon("unknown")


# ---------------------------------------------------------------------------
# CSS contains new selectors
# ---------------------------------------------------------------------------


class TestHealthCSS:
    def test_health_state_in_css(self):
        assert "#health-state" in ConsoleApp.CSS

    def test_data_paths_in_css(self):
        assert "#data-paths" in ConsoleApp.CSS

    def test_health_green_class_in_css(self):
        assert "health-green" in ConsoleApp.CSS

    def test_health_yellow_class_in_css(self):
        assert "health-yellow" in ConsoleApp.CSS

    def test_health_red_class_in_css(self):
        assert "health-red" in ConsoleApp.CSS
