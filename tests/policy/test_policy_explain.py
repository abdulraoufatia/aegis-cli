"""Tests for atlasbridge.core.policy.explain — explain_decision() and explain_policy()."""

from __future__ import annotations

from pathlib import Path

from atlasbridge.core.policy.explain import explain_decision, explain_policy
from atlasbridge.core.policy.model import (
    AutoReplyAction,
    DenyAction,
    NotifyOnlyAction,
    PolicyDecision,
    RequireHumanAction,
)
from atlasbridge.core.policy.parser import load_policy

_FIXTURES = Path(__file__).parent / "fixtures"
_FIXTURES_V1 = _FIXTURES / "v1"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_decision(
    *,
    action_type: str = "auto_reply",
    action_value: str = "y",
    matched_rule_id: str | None = "test-rule",
    confidence: str = "high",
    prompt_type: str = "yes_no",
    explanation: str = "Rule matched",
) -> PolicyDecision:
    """Build a minimal PolicyDecision for testing."""
    actions = {
        "auto_reply": AutoReplyAction(value=action_value),
        "require_human": RequireHumanAction(),
        "deny": DenyAction(reason="blocked"),
        "notify_only": NotifyOnlyAction(message="heads up"),
    }
    return PolicyDecision(
        prompt_id="p1",
        session_id="s1",
        policy_hash="abc123",
        matched_rule_id=matched_rule_id,
        action=actions[action_type],
        explanation=explanation,
        confidence=confidence,
        prompt_type=prompt_type,
        autonomy_mode="full",
    )


# ---------------------------------------------------------------------------
# explain_decision() tests
# ---------------------------------------------------------------------------


class TestExplainDecision:
    def test_auto_reply_all_fields(self):
        decision = _make_decision(action_type="auto_reply", action_value="y")
        output = explain_decision(decision)
        assert "AUTO_REPLY" in output
        assert "'y'" in output
        assert "test-rule" in output
        assert "high" in output
        assert "yes_no" in output
        assert "full" in output
        assert "abc123" in output
        assert "Rule matched" in output

    def test_require_human_no_matched_rule(self):
        decision = _make_decision(
            action_type="require_human",
            matched_rule_id=None,
            explanation="No rule matched",
        )
        output = explain_decision(decision)
        assert "REQUIRE_HUMAN" in output
        assert "(none" in output
        # No "Reply value" line for require_human (action_value is empty)
        assert "Reply value" not in output

    def test_deny_shows_action_type(self):
        decision = _make_decision(action_type="deny", explanation="Destructive op denied")
        output = explain_decision(decision)
        assert "DENY" in output
        assert "Destructive op denied" in output

    def test_notify_only_shows_action_type(self):
        decision = _make_decision(action_type="notify_only", explanation="Notified only")
        output = explain_decision(decision)
        assert "NOTIFY_ONLY" in output

    def test_all_labeled_fields_present(self):
        decision = _make_decision()
        output = explain_decision(decision)
        expected_labels = [
            "Decision:",
            "Matched rule:",
            "Confidence:",
            "Prompt type:",
            "Autonomy mode:",
            "Policy hash:",
            "Idem key:",
            "Explanation:",
        ]
        for label in expected_labels:
            assert label in output, f"Missing label: {label}"

    def test_reply_value_shown_for_auto_reply(self):
        decision = _make_decision(action_type="auto_reply", action_value="n")
        output = explain_decision(decision)
        assert "Reply value:" in output
        assert "'n'" in output


# ---------------------------------------------------------------------------
# explain_policy() tests — v0
# ---------------------------------------------------------------------------


class TestExplainPolicyV0:
    def test_first_rule_matches(self):
        policy = load_policy(_FIXTURES / "basic.yaml")
        output = explain_policy(
            policy,
            prompt_text="Continue? [y/n]",
            prompt_type="yes_no",
            confidence="high",
        )
        assert "MATCH" in output
        assert "yes-no-auto-yes" in output
        assert "first match wins" in output.lower()

    def test_no_match_shows_default(self):
        policy = load_policy(_FIXTURES / "basic.yaml")
        output = explain_policy(
            policy,
            prompt_text="What file?",
            prompt_type="free_text",
            confidence="high",
        )
        assert "No rule matched" in output
        assert "require_human" in output

    def test_skip_with_wrong_prompt_type(self):
        policy = load_policy(_FIXTURES / "basic.yaml")
        output = explain_policy(
            policy,
            prompt_text="Continue? [y/n]",
            prompt_type="free_text",
            confidence="high",
        )
        # First rule should be skipped (prompt_type mismatch), shown as "skip"
        assert "skip" in output.lower()

    def test_deny_rule_match(self):
        policy = load_policy(_FIXTURES / "escalation.yaml")
        output = explain_policy(
            policy,
            prompt_text="Are you sure you want to rm -rf /?",
            prompt_type="yes_no",
            confidence="high",
        )
        assert "MATCH" in output
        assert "deny-destructive" in output

    def test_confidence_filter(self):
        policy = load_policy(_FIXTURES / "basic.yaml")
        # yes-no-auto-yes requires min_confidence: medium, so low should skip it
        output = explain_policy(
            policy,
            prompt_text="Continue? [y/n]",
            prompt_type="yes_no",
            confidence="low",
        )
        # Should skip the first rule (low < medium) and not match
        assert "skip" in output.lower()

    def test_policy_header_shows_name_and_hash(self):
        policy = load_policy(_FIXTURES / "basic.yaml")
        output = explain_policy(
            policy,
            prompt_text="test",
            prompt_type="yes_no",
            confidence="high",
        )
        assert "basic" in output
        assert "version=" in output
        assert "hash=" in output


# ---------------------------------------------------------------------------
# explain_policy() tests — v1
# ---------------------------------------------------------------------------


class TestExplainPolicyV1:
    def test_any_of_match(self):
        policy = load_policy(_FIXTURES_V1 / "any_of_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="Continue?",
            prompt_type="yes_no",
            confidence="high",
        )
        assert "MATCH" in output
        assert "any-of-rule" in output
        assert "any_of" in output

    def test_any_of_second_branch(self):
        policy = load_policy(_FIXTURES_V1 / "any_of_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="Press enter",
            prompt_type="confirm_enter",
            confidence="high",
        )
        assert "MATCH" in output
        assert "any-of-rule" in output

    def test_none_of_allows_safe_prompt(self):
        policy = load_policy(_FIXTURES_V1 / "none_of_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="Continue? [y/n]",
            prompt_type="yes_no",
            confidence="high",
        )
        assert "MATCH" in output
        assert "safe-auto-reply" in output
        assert "none_of" in output

    def test_none_of_blocks_excluded_word(self):
        policy = load_policy(_FIXTURES_V1 / "none_of_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="destroy all data? [y/n]",
            prompt_type="yes_no",
            confidence="high",
        )
        # First rule should NOT match because "destroy" is in none_of
        # catch-all should match instead
        assert "catch-all" in output

    def test_session_tag_matching(self):
        policy = load_policy(_FIXTURES_V1 / "session_tag_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="Continue? [y/n]",
            prompt_type="yes_no",
            confidence="high",
            session_tag="ci",
        )
        assert "MATCH" in output
        assert "ci-auto-reply" in output

    def test_session_tag_non_matching(self):
        policy = load_policy(_FIXTURES_V1 / "session_tag_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="Continue? [y/n]",
            prompt_type="yes_no",
            confidence="high",
            session_tag="dev",
        )
        # ci-auto-reply should skip (session_tag mismatch), catch-all matches
        assert "catch-all" in output

    def test_session_tag_input_shown(self):
        policy = load_policy(_FIXTURES_V1 / "session_tag_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="test",
            prompt_type="yes_no",
            confidence="high",
            session_tag="ci",
        )
        assert "session_tag=" in output

    def test_repo_input_shown(self):
        policy = load_policy(_FIXTURES_V1 / "session_tag_match.yaml")
        output = explain_policy(
            policy,
            prompt_text="test",
            prompt_type="yes_no",
            confidence="high",
            repo="/home/user/project",
        )
        assert "repo=" in output
