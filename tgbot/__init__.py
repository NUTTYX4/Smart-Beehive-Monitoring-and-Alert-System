"""Telegram integration subpackage: alert dispatch, bot commands, and keyboards.

Named `tgbot` rather than `telegram` on purpose: a local package named
`telegram` would shadow the installed `python-telegram-bot` library
(which is imported as `telegram`) whenever the project directory is
on `sys.path`, breaking every `from telegram import ...` statement in
this codebase. Keeping this package under a distinct name avoids that
collision entirely.
"""
