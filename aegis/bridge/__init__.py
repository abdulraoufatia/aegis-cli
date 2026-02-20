"""
aegis.bridge — Tool interception adapters.

The bridge layer wraps AI CLI tools in a PTY or pipe, intercepts their
tool call events, and routes them through the policy engine.

Modules:
    base            Abstract ToolAdapter interface
    pty_adapter     PTY-based wrapper (primary, POSIX)
    pipe_adapter    Pipe-based wrapper (fallback)
    interceptor     Tool call event parser and router
    adapters/       Per-tool adapter implementations
"""
