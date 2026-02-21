"""
aegis.audit — Append-only audit log.

The audit log is stored separately from the SQLite database as a
JSON Lines file with a hash chain for tamper-evidence.

Modules:
    writer      Append-only log writer (O_APPEND, hash chain)
    reader      Log reader, query, and filtering
    integrity   Hash chain verification (used by aegis doctor)
"""
