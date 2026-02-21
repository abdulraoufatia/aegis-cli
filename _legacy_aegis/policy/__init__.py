"""
aegis.policy — Policy engine for evaluating tool calls against rules.

Modules:
    engine      Rule evaluation loop (first-match, priority-ordered)
    loader      TOML policy file parser and validator
    models      Policy rule and decision data models
    risk        Risk scoring heuristics
    defaults    Hardcoded built-in safety rules (cannot be overridden)
"""
