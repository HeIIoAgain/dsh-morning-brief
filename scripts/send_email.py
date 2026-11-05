#!/usr/bin/env python3
"""Send the morning brief over SMTP.

Fallback for hosts that do not provide a ``send_email`` tool. Reads
``delivery.smtp`` from ``config.json``; the password is **never** stored in the
file — it is read from the environment variable named by ``password_env``
(default: ``MORNING_BRIEF_SMTP_PASSWORD``).

Examples
--------
    export MORNING_BRIEF_SMTP_PASSWORD='app-password'
    python3 scripts/send_email.py --config config.json \\
        --subject "半导体晨报 · 2026-10-09" \\
        --body-file body.txt --attach reports/半导体晨报2026年10月9日.docx

    python3 scripts/send_email.py --config config.json --dry-run --body-file body.txt
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_DIR / "config.json"


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def now_in(timezone_name: str | None) -> datetime:
    if timezone_name:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo(timezone_name))
        except Exception:  # noqa: BLE001 - fall back to local time
            pass
    return datetime.now()


def render_subject(template: str, config: dict) -> str:
    moment = now_in(config.get("timezone"))
    return (
        template.replace("{date}", moment.strftime("%Y-%m-%d"))
        .replace("{datetime}", moment.strftime("%Y-%m-%d %H:%M"))
    )


def build_message(
    config: dict,
    subject: str,
    body: str,
    recipient: str,
    attachments: list[Path],
) -> tuple[EmailMessage, dict]:
    smtp = (config.get("delivery") or {}).get("smtp") or {}
    sender = smtp.get("from") or smtp.get("username")
    if not sender:
        raise SystemExit("config error: delivery.smtp.from (or username) is required")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    for path in attachments:
        path = path.expanduser()
        if not path.is_file():
            raise SystemExit(f"attachment not found: {path}")
        guessed, _ = mimetypes.guess_type(path.name)
        maintype, subtype = guessed.split("/", 1) if guessed else ("application", "octet-stream")
        message.add_attachment(
            path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name
        )
    return message, smtp


def send(message: EmailMessage, smtp: dict) -> None:
    host = smtp.get("host")
    if not host:
        raise SystemExit("config error: delivery.smtp.host is required")
    use_ssl = bool(smtp.get("ssl", True))
    port = int(smtp.get("port") or (465 if use_ssl else 587))
    username = smtp.get("username") or smtp.get("from")
    password_env = smtp.get("password_env") or "MORNING_BRIEF_SMTP_PASSWORD"
    password = os.environ.get(password_env)
    if not password:
        raise SystemExit(
            f"missing SMTP password: export {password_env}=<app-password> and retry"
        )

    context = ssl.create_default_context()
    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=45, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=45)
        server.starttls(context=context)

    with server:
        server.login(username, password)
        refused = server.send_message(message)
    if refused:
        raise SystemExit(f"some recipients were refused: {refused}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send the morning brief over SMTP.")
    parser.add_argument(
        "--config",
        default=os.environ.get("MORNING_BRIEF_CONFIG", str(DEFAULT_CONFIG)),
        help="path to config.json (default: $MORNING_BRIEF_CONFIG or <skill>/config.json)",
    )
    parser.add_argument("--subject", help="subject line; defaults to config.subject")
    parser.add_argument("--body-file", required=True, help="plain-text email body")
    parser.add_argument("--attach", action="append", default=[], help="attachment path (repeatable)")
    parser.add_argument("--to", help="override the recipient")
    parser.add_argument("--dry-run", action="store_true", help="build the message but do not send")
    args = parser.parse_args(argv)

    config_path = Path(args.config).expanduser()
    if not config_path.is_file():
        raise SystemExit(f"config not found: {config_path}")

    config = load_config(config_path)
    recipient = args.to or config.get("recipient")
    if not recipient:
        raise SystemExit("config error: recipient is required")

    subject_template = args.subject or config.get("subject")
    if not subject_template:
        raise SystemExit("config error: subject is required")

    body_path = Path(args.body_file).expanduser()
    if not body_path.is_file():
        raise SystemExit(f"body file not found: {body_path}")

    subject = render_subject(subject_template, config)
    message, smtp = build_message(
        config,
        subject,
        body_path.read_text(encoding="utf-8"),
        recipient,
        [Path(item) for item in args.attach],
    )

    if args.dry_run:
        print(f"dry run: would send {subject!r} to {recipient}")
        for item in args.attach:
            print(f"  attachment: {item}")
        return 0

    send(message, smtp)
    print(f"sent: {subject!r} -> {recipient} ({len(args.attach)} attachment(s))")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
