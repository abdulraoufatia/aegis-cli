# Aegis Policy Engine Design

**Version:** 0.1.0
**Status:** Design
**Last updated:** 2026-02-20

---

## Overview

The policy engine is the core decision-making component of Aegis. It evaluates every tool call against a set of ordered rules and returns one of three actions: `allow`, `deny`, or `require_approval`.

**Design goals:**
- Fast (rule evaluation < 1ms for typical cases)
- Safe (unknown → require_approval; error → deny)
- Expressive (pattern matching on tool name, path, command, risk tier)
- Ordered (rules evaluated by priority; first match wins)
- Auditable (every decision logged with the matching rule)

---

## Policy File Format

Policy is stored in `~/.aegis/policy.toml`. TOML was chosen for readability, comments, and wide tooling support.

### Minimal policy

```toml
[policy]
default_action = "require_approval"
```

### Full policy example

```toml
# ~/.aegis/policy.toml
# Aegis Policy Configuration

[policy]
# Fail-safe default: what to do if no rule matches
# Options: allow | deny | require_approval
# Default: require_approval (recommended)
default_action = "require_approval"

# --- Read operations ---

[[policy.rules]]
name = "allow-read-src"
description = "Allow reading source files in the project"
match = { tool = "read_file", path_pattern = "^/Users/ara/project/.*\\.(py|js|ts|go|rs|md)$" }
action = "allow"
priority = 100

[[policy.rules]]
name = "block-secret-reads"
description = "Block reading secret and credential files"
match = { tool = "read_file", path_pattern = ".*\\.env.*|.*\\.pem|.*\\.key|.*credentials.*|.*secret.*|\\.ssh/.*|\\.aws/.*|\\.gnupg/.*" }
action = "deny"
reason = "Secret file access is prohibited"
priority = 10   # Low priority number = evaluated first

[[policy.rules]]
name = "require-approval-reads-outside-project"
description = "Require approval for reading files outside the project directory"
match = { tool = "read_file" }
action = "require_approval"
priority = 90

# --- Write operations ---

[[policy.rules]]
name = "block-aegis-config-writes"
description = "Never allow writing to Aegis config directory"
match = { tool = "write_file", path_pattern = ".*\\.aegis/.*" }
action = "deny"
reason = "Aegis configuration files cannot be modified by AI agents"
priority = 5

[[policy.rules]]
name = "require-approval-writes"
description = "All writes require approval"
match = { tool = "write_file" }
action = "require_approval"
priority = 80

# --- Delete operations ---

[[policy.rules]]
name = "block-all-deletes"
description = "Never allow file deletion without approval"
match = { tool = "delete_file" }
action = "require_approval"
priority = 50

# --- Shell / bash ---

[[policy.rules]]
name = "block-force-push"
description = "Force push to remote is prohibited"
match = { tool = "bash", command_pattern = "git push.*(--force|-f)" }
action = "deny"
reason = "Force push to remote is prohibited. Use a PR instead."
priority = 5

[[policy.rules]]
name = "block-rm-rf"
description = "Recursive force delete is prohibited without explicit approval"
match = { tool = "bash", command_pattern = "rm\\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\\s+-[a-zA-Z]*f[a-zA-Z]*r" }
action = "require_approval"
priority = 10

[[policy.rules]]
name = "block-curl-exfil"
description = "Curl/wget to external URLs is blocked"
match = { tool = "bash", command_pattern = "(curl|wget)\\s+.*(https?://(?!api\\.telegram\\.org))" }
action = "deny"
reason = "External HTTP requests from AI agents are blocked"
priority = 5

[[policy.rules]]
name = "allow-safe-shell"
description = "Allow read-only shell commands"
match = { tool = "bash", command_pattern = "^(ls|cat|head|tail|grep|find|echo|pwd|which|type|file|stat|wc)\\s" }
action = "allow"
priority = 70

[[policy.rules]]
name = "require-approval-shell"
description = "All other shell commands require approval"
match = { tool = "bash" }
action = "require_approval"
priority = 60

# --- Package installation ---

[[policy.rules]]
name = "require-approval-pip"
description = "Package installation requires approval"
match = { tool = "bash", command_pattern = "(pip|pip3|poetry|uv)\\s+install" }
action = "require_approval"
priority = 15
risk_tier = "high"

[[policy.rules]]
name = "block-npm-global"
description = "Global npm install is blocked"
match = { tool = "bash", command_pattern = "npm\\s+install.*-g|npm\\s+install.*--global" }
action = "deny"
reason = "Global package installation is prohibited"
priority = 5
```

---

## Rule Structure

Each rule has the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the rule |
| `description` | string | No | Human-readable description |
| `match` | object | Yes | Matching criteria (see below) |
| `action` | enum | Yes | `allow` \| `deny` \| `require_approval` |
| `priority` | integer | Yes | Evaluation order (lower = higher priority) |
| `reason` | string | No | Displayed to user when action is deny/block |
| `risk_tier` | enum | No | `low` \| `medium` \| `high` \| `critical` |

---

## Match Criteria

The `match` object supports these fields:

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Exact tool name (e.g., `"read_file"`, `"bash"`, `"write_file"`) |
| `path_pattern` | regex | Python regex matched against normalized file path |
| `command_pattern` | regex | Python regex matched against shell command string |
| `arg_pattern` | dict | Key-value where value is a regex matched against that argument |
| `risk_tier` | enum | Match by risk tier assigned by risk scorer |
| `session_id` | string | Match specific session (for dynamic rules) |

All regex patterns use Python's `re` module with `re.IGNORECASE` by default.

---

## Rule Evaluation Algorithm

```python
def evaluate(tool_call: ToolCall, rules: list[Rule]) -> PolicyDecision:
    # Normalize paths before matching
    if tool_call.has_path_arg():
        tool_call.path = os.path.realpath(tool_call.path)

    # Sort rules by priority (ascending — lower number = higher priority)
    sorted_rules = sorted(rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        if rule.matches(tool_call):
            return PolicyDecision(
                action=rule.action,
                matched_rule=rule.name,
                reason=rule.reason,
            )

    # No rule matched — apply default action (fail-safe)
    return PolicyDecision(
        action=policy.default_action,
        matched_rule="default",
        reason="No matching rule — default action applied",
    )
```

**Key properties:**
- Rules are evaluated in priority order (lowest number first)
- First match wins — evaluation stops
- If no rule matches, the `default_action` applies
- Default action default value: `require_approval`
- On any evaluation error (malformed rule, regex error): action = `deny`

---

## Risk Scoring

Each tool call receives a risk score before policy evaluation. The risk score is used for:
- Default priority when no explicit rule matches
- Approval message urgency level
- Audit log categorization

```python
class RiskTier(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

RISK_MATRIX = {
    # (tool_name, heuristic) → RiskTier
    ("read_file", "in_project_dir"): RiskTier.LOW,
    ("read_file", "outside_project_dir"): RiskTier.MEDIUM,
    ("read_file", "secret_file_pattern"): RiskTier.CRITICAL,
    ("write_file", "in_project_dir"): RiskTier.MEDIUM,
    ("write_file", "outside_project_dir"): RiskTier.HIGH,
    ("write_file", "aegis_config"): RiskTier.CRITICAL,
    ("delete_file", "*"): RiskTier.HIGH,
    ("bash", "read_only_cmd"): RiskTier.LOW,
    ("bash", "git_push_force"): RiskTier.CRITICAL,
    ("bash", "rm_rf"): RiskTier.HIGH,
    ("bash", "package_install"): RiskTier.HIGH,
    ("bash", "curl_external"): RiskTier.CRITICAL,
    ("bash", "other"): RiskTier.MEDIUM,
}
```

Risk tier is shown in Telegram approval messages to help the user make informed decisions.

---

## Built-in Default Rules

These rules are hardcoded in `policy/defaults.py` and cannot be overridden by user policy (they are evaluated before user rules for the critical cases):

```python
HARDCODED_DENY_RULES = [
    # Never allow writing to Aegis own config dir
    Rule(
        name="__hardcoded__aegis-config-protect",
        match={"tool": "write_file", "path_pattern": r".*\.aegis/.*"},
        action="deny",
        reason="Aegis configuration is protected and cannot be modified by AI agents",
        priority=1,  # Evaluated first, always
    ),
    # Never allow reading the Telegram bot token file
    Rule(
        name="__hardcoded__aegis-token-protect",
        match={"tool": "read_file", "path_pattern": r".*\.aegis/config\.toml"},
        action="deny",
        reason="Aegis configuration contains secrets and cannot be read by AI agents",
        priority=1,
    ),
]
```

These rules are documented clearly and cannot be silently overridden.

---

## Policy Validation

When loading policy (at startup or SIGHUP reload), the engine validates:

1. TOML parses without error
2. `[policy]` section exists
3. `default_action` is a valid enum value
4. All rules have `name`, `match`, `action`, `priority`
5. All rule `action` values are valid enum values
6. All regex patterns compile without error
7. No two rules have the same `name`
8. No two rules have the same `priority` (warning, not error)

If validation fails:
- At startup: exit 2 with clear error message
- At reload (SIGHUP): reject new policy, keep current policy, log error

---

## Policy Diff on Reload

When policy is reloaded, the daemon logs a structured diff:

```
[2026-02-20 19:00:00] INFO  Policy reloaded
  Added rules:    1 (allow-read-tests)
  Removed rules:  0
  Changed rules:  1 (require-approval-reads: priority 90→85)
  Unchanged:      12
```

---

## RBAC Integration

Future: Policy rules can be scoped to RBAC roles:

```toml
[[policy.rules]]
name = "allow-admin-shell"
match = { tool = "bash" }
action = "allow"
priority = 50
roles = ["admin"]   # Only applies when the approver has admin role
```

Phase 2 MVP uses a simple flat whitelist. RBAC roles are Phase 4.

---

## Performance

Target: < 1ms per policy evaluation for typical rule sets (< 100 rules).

- Rules are compiled (regex pre-compiled) at load time, not at evaluation time
- Path normalization is cached per tool call (realpath is O(1) for most paths)
- Policy is reloaded only on SIGHUP or explicit reload command
- Policy cache TTL: 60 seconds for dynamic rules (Phase 4)

---

## Testing Policy

```bash
# Dry-run a tool call against current policy
aegis policy check --tool write_file --path /src/main.py

# Output:
# Tool:    write_file
# Path:    /Users/ara/project/src/main.py (normalized)
# Rule:    require-approval-writes (priority 80)
# Action:  require_approval
# Risk:    MEDIUM

# Validate policy file
aegis config validate

# Show all rules in evaluation order
aegis policy list
```
