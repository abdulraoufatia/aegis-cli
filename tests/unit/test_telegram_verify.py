"""Unit tests for atlasbridge.channels.telegram.verify."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestVerifyTelegramToken:
    """Tests for verify_telegram_token()."""

    def test_valid_token_returns_ok(self) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "result": {"id": 123, "is_bot": True, "username": "mybot"},
        }
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            from atlasbridge.channels.telegram.verify import verify_telegram_token

            ok, detail = verify_telegram_token("123456789:ABCDEF")

        assert ok is True
        assert detail == "Bot: @mybot"
        mock_get.assert_called_once()

    def test_invalid_token_returns_false(self) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": False,
            "error_code": 401,
            "description": "Unauthorized",
        }
        with patch("httpx.get", return_value=mock_resp):
            from atlasbridge.channels.telegram.verify import verify_telegram_token

            ok, detail = verify_telegram_token("bad-token")

        assert ok is False
        assert "Unauthorized" in detail

    def test_network_error_returns_false(self) -> None:
        import httpx

        with patch("httpx.get", side_effect=httpx.ConnectError("DNS failed")):
            from atlasbridge.channels.telegram.verify import verify_telegram_token

            ok, detail = verify_telegram_token("123456789:ABCDEF")

        assert ok is False
        assert "Could not connect" in detail

    def test_timeout_returns_false(self) -> None:
        import httpx

        with patch("httpx.get", side_effect=httpx.TimeoutException("timed out")):
            from atlasbridge.channels.telegram.verify import verify_telegram_token

            ok, detail = verify_telegram_token("123456789:ABCDEF")

        assert ok is False
        assert "timed out" in detail.lower()
