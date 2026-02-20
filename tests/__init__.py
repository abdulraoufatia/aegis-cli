"""
Aegis test suite.

Tests are organized by layer:
    tests/unit/         Unit tests (no I/O, fast)
    tests/integration/  Integration tests (SQLite, HTTP mocks)
    tests/e2e/          End-to-end tests (Phase 4)

Run all tests:
    pytest

Run with coverage:
    pytest --cov=aegis

Run unit tests only:
    pytest tests/unit/ -m unit
"""
