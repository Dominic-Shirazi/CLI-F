"""
CEO communication layer — sends LangGraph interrupt alerts and waits for a reply.

Telegram mode: set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env
Terminal fallback: if env vars are missing, blocks on input() instead.

Usage (from main.py):
    reply = ceo_comms.wait_for_reply(alert_text, timeout=3600)
"""

import os
import time
import requests
from typing import Optional


def _token() -> str:
    return os.environ["TELEGRAM_BOT_TOKEN"]


def _chat_id() -> str:
    return os.environ["TELEGRAM_CHAT_ID"]


def _is_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def send_message(text: str) -> None:
    """Fire-and-forget: send a message to the CEO's Telegram chat."""
    url = f"https://api.telegram.org/bot{_token()}/sendMessage"
    try:
        requests.post(
            url,
            json={"chat_id": _chat_id(), "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"[Telegram] Failed to send message: {e}")


def _get_update_offset() -> int:
    """Return update_id + 1 of the most recent update so we skip history."""
    url = f"https://api.telegram.org/bot{_token()}/getUpdates"
    try:
        resp = requests.get(url, params={"limit": 1, "offset": -1}, timeout=10)
        updates = resp.json().get("result", [])
        if updates:
            return updates[-1]["update_id"] + 1
    except requests.RequestException:
        pass
    return 0


def _poll_for_reply(offset: int, poll_interval: int = 5) -> tuple[Optional[str], int]:
    """
    Long-poll Telegram once. Returns (message_text, new_offset) if a new message
    arrived from the CEO chat, or (None, offset) if nothing yet.
    """
    url = f"https://api.telegram.org/bot{_token()}/getUpdates"
    try:
        resp = requests.get(
            url,
            params={"offset": offset, "timeout": poll_interval},
            timeout=poll_interval + 5,
        )
        updates = resp.json().get("result", [])
        for update in updates:
            new_offset = update["update_id"] + 1
            msg = update.get("message", {})
            if str(msg.get("chat", {}).get("id", "")) == _chat_id():
                return msg.get("text", "").strip(), new_offset
            offset = new_offset
    except requests.RequestException as e:
        print(f"[Telegram] Poll error: {e}")
    return None, offset


def wait_for_reply(alert_text: str, timeout: int = 3600) -> str:
    """
    Send alert_text to CEO and block until they reply.
    Returns the raw reply string.

    Falls back to terminal input() if Telegram is not configured.
    Raises TimeoutError if no reply arrives within `timeout` seconds.
    """
    if not _is_configured():
        print(f"\n[CEO REVIEW]\n{alert_text}\n")
        return input("Enter your instructions (or ABORT to stop): ").strip()

    offset = _get_update_offset()
    send_message(alert_text)
    print(f"[Telegram] Alert sent. Waiting for CEO reply (timeout: {timeout}s)...")

    deadline = time.time() + timeout
    while time.time() < deadline:
        reply, offset = _poll_for_reply(offset)
        if reply is not None:
            print(f"[Telegram] CEO replied: {reply!r}")
            return reply

    raise TimeoutError(f"No CEO reply received within {timeout} seconds.")
