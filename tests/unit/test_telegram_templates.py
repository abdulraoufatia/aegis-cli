"""Unit tests for TelegramChannel prompt formatting and keyboard building."""

from __future__ import annotations

from aegis.channels.telegram.channel import TelegramChannel
from aegis.core.prompt.models import Confidence, PromptEvent, PromptType

_VALID_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"


def _channel() -> TelegramChannel:
    return TelegramChannel(bot_token=_VALID_TOKEN, allowed_user_ids=[12345])


def _event(prompt_type: PromptType, choices: list[str] | None = None) -> PromptEvent:
    return PromptEvent.create(
        session_id="test-session-abc",
        prompt_type=prompt_type,
        confidence=Confidence.HIGH,
        excerpt="Continue? (y/n)",
        choices=choices or [],
    )


class TestFormatPrompt:
    def test_yes_no_contains_session(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_YES_NO)
        text = ch._format_prompt(event)
        assert "test-ses" in text  # first 8 chars of session_id

    def test_yes_no_shows_type_label(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_YES_NO)
        text = ch._format_prompt(event)
        assert "Yes / No" in text

    def test_confirm_enter_shows_label(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_CONFIRM_ENTER)
        text = ch._format_prompt(event)
        assert "Press Enter" in text

    def test_free_text_shows_label(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_FREE_TEXT)
        text = ch._format_prompt(event)
        assert "Free Text" in text


class TestBuildKeyboard:
    def test_yes_no_has_yes_and_no(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_YES_NO)
        kb = ch._build_keyboard(event)
        assert len(kb) == 1
        texts = [b["text"] for b in kb[0]]
        assert "Yes" in texts
        assert "No" in texts

    def test_yes_no_callback_contains_prompt_id(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_YES_NO)
        kb = ch._build_keyboard(event)
        all_data = [b["callback_data"] for b in kb[0]]
        assert all(event.prompt_id in d for d in all_data)

    def test_confirm_enter_has_send_enter(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_CONFIRM_ENTER)
        kb = ch._build_keyboard(event)
        texts = [b["text"] for b in kb[0]]
        assert any("Enter" in t for t in texts)

    def test_multiple_choice_one_button_per_choice(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_MULTIPLE_CHOICE, choices=["Alpha", "Beta", "Gamma"])
        kb = ch._build_keyboard(event)
        assert len(kb[0]) == 3

    def test_free_text_no_buttons(self) -> None:
        ch = _channel()
        event = _event(PromptType.TYPE_FREE_TEXT)
        kb = ch._build_keyboard(event)
        assert kb == []
