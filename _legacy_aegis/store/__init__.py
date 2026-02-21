"""
aegis.store — SQLite persistence layer.

Manages the local database for approval records, session state, and
policy events. Uses raw sqlite3 (no ORM dependency).

Modules:
    database            Connection management, WAL mode, migrations
    migrations/         SQL migration files (001_initial.sql, etc.)
    repositories/       Per-entity repository classes
        approval_repo   CRUD for approvals table
        session_repo    CRUD for sessions table
        audit_repo      Read access to audit log metadata
    models              Typed dataclasses for all stored entities
"""
