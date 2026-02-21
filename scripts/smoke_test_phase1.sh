#!/usr/bin/env bash
# ============================================================================
# AtlasBridge Phase 1 — Core Runtime Kernel Smoke Test
#
# Run this script after install to verify all Phase 1 exit criteria pass.
# Usage: bash scripts/smoke_test_phase1.sh
# ============================================================================

set -euo pipefail

PASS=0
FAIL=0
WARN=0

pass() { echo "  ✓ PASS  $1"; ((PASS++)); }
fail() { echo "  ✗ FAIL  $1"; ((FAIL++)); }
warn() { echo "  ⚠ WARN  $1"; ((WARN++)); }

echo "============================================"
echo "AtlasBridge Phase 1 — Smoke Test"
echo "============================================"
echo

# ------------------------------------------------------------------
# A) Fresh install works
# ------------------------------------------------------------------
echo "--- A) Fresh install ---"

if atlasbridge version >/dev/null 2>&1; then
    VER=$(atlasbridge version 2>&1 | head -1)
    pass "atlasbridge version: $VER"
else
    fail "atlasbridge version failed"
fi

if atlasbridge doctor --json >/dev/null 2>&1; then
    pass "atlasbridge doctor runs without error"
else
    warn "atlasbridge doctor has warnings (check output)"
fi

# ------------------------------------------------------------------
# B) Upgrade safety — DB auto-creates
# ------------------------------------------------------------------
echo
echo "--- B) Database ---"

if atlasbridge db info >/dev/null 2>&1; then
    pass "atlasbridge db info runs without error"
else
    fail "atlasbridge db info failed"
fi

# ------------------------------------------------------------------
# C) Deterministic adapter registry
# ------------------------------------------------------------------
echo
echo "--- C) Adapter registry ---"

ADAPTER_OUT=$(atlasbridge adapter list 2>&1)
if echo "$ADAPTER_OUT" | grep -q "claude"; then
    pass "adapter list shows claude"
else
    fail "adapter list missing claude"
fi

if echo "$ADAPTER_OUT" | grep -q "openai"; then
    pass "adapter list shows openai"
else
    fail "adapter list missing openai"
fi

if echo "$ADAPTER_OUT" | grep -q "gemini"; then
    pass "adapter list shows gemini"
else
    fail "adapter list missing gemini"
fi

# ------------------------------------------------------------------
# D) Tests pass
# ------------------------------------------------------------------
echo
echo "--- D) Test suite ---"

if python3 -m pytest tests/ -q --tb=line 2>&1 | tail -1 | grep -q "passed"; then
    RESULT=$(python3 -m pytest tests/ -q --tb=line 2>&1 | tail -1)
    pass "pytest: $RESULT"
else
    RESULT=$(python3 -m pytest tests/ -q --tb=line 2>&1 | tail -1)
    fail "pytest: $RESULT"
fi

# ------------------------------------------------------------------
# E) Lint clean
# ------------------------------------------------------------------
echo
echo "--- E) Lint ---"

if python3 -m ruff check src/ tests/ >/dev/null 2>&1; then
    pass "ruff check clean"
else
    fail "ruff check has errors"
fi

if python3 -m ruff format --check src/ tests/ >/dev/null 2>&1; then
    pass "ruff format clean"
else
    fail "ruff format has diffs"
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo
echo "============================================"
echo "Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    echo "PHASE 1 STATUS: NOT READY"
    exit 1
else
    echo "PHASE 1 STATUS: READY"
    exit 0
fi
