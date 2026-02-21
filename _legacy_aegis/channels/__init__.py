"""
aegis.channels — Approval routing channels.

Channels are responsible for delivering approval requests to users
and receiving their decisions.

Available channels:
    telegram/   Telegram bot (long polling) — Phase 2 MVP
    whatsapp/   WhatsApp adapter — Phase 3

All channels implement the abstract BaseChannel interface defined
in base.py, making them interchangeable.
"""
