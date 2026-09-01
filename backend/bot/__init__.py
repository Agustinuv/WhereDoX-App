"""Telegram adapter.

This package receives updates and translates them into service calls. It holds no rules:
who may vote, how a tally ranks and when a date can be confirmed all still live in
app/services, unchanged and shared with the REST API.

The dependency only points one way — bot/ imports app/, never the reverse — which is what
lets the API run with no bot and the bot run against the same decisions.
"""
