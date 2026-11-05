#!/usr/bin/env python3
"""Self-check for the morning-brief skill repository.

Usage
-----
    python3 scripts/validate.py               # full check (repo + local config.json if present)
    python3 scripts/validate.py --repo-only   # repo checks only, config not required (used by CI)

Exit code 0 means everything passed; 1 lists the failures.
"""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "README.en.md",
    "LICENSE",
    "CHANGELOG.md",
    "config.example.json",
]

REQUIRED_REFERENCES = [
    "references/handbook.md",
    "references/watchlist.md",
    "references/report-template.md",
    "references/output-spec.md",
    "references/schedule.md",
]

REQUIRED_SCRIPTS = [
    "scripts/md2docx.py",
    "scripts/send_email.py",
    "scripts/install.sh",
]

ALLOWED_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "users.noreply.github.com",
}

SECRET_PATTERNS = [
    (re.compile(r"/home/[A-Za-z0-9._-]+/"), "absolute home path"),
    (re.compile(r"/Users/[A-Za-z0-9._-]+/"), "absolute macOS home path"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "email address"),
    (
        re.compile(
            r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"][^'\"]{6,}['\"]"
        ),
        "inline secret",
    ),
]

SKIP_DIRS = {".git", "__pycache__", "reports", ".venv", "venv", ".idea", ".vscode"}
SKIP_FILES = {"config.json"}
BINARY_SUFFIXES = {".docx", ".doc", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".gz", ".pdf"}

failures: list[str] = []
warnings: list[str] = []


def ok(message: str) -> None:
    print(f"OK      {message}")


def warn(message: str) -> None:
    warnings.append(message)
    print(f"WARN    {message}")


def fail(message: str) -> None:
    failures.append(message)
    print(f"FAIL    {message}")


def check_file(rel: str) -> None:
    path = ROOT / rel
    if path.is_file() and path.stat().st_size > 0:
        ok(rel)
    else:
        fail(f"{rel} missing or empty")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        raise ValueError("does not start with '---'")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("frontmatter is not closed")
    block = text[3:end]
    data: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {raw!r}")
        data[key.strip()] = value.strip()
    return data


def check_skill_frontmatter() -> None:
    path = ROOT / "SKILL.md"
    if not path.is_file():
        return
    try:
        data = parse_frontmatter(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        fail(f"SKILL.md frontmatter: {exc}")
        return
    name = data.get("name", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        fail(f"SKILL.md frontmatter name is not kebab-case: {name!r}")
    else:
        ok(f"SKILL.md name={name}")
    description = data.get("description", "")
    if len(description) < 40:
        fail("SKILL.md frontmatter description is too short")
    else:
        ok("SKILL.md description present")
    if not data.get("whenToUse"):
        warn("SKILL.md has no whenToUse hint")
    else:
        ok("SKILL.md whenToUse present")


def check_json_config(path: Path, *, is_example: bool) -> None:
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {exc}")
        return
    required = ["recipient", "report_dir", "delivery"]
    missing = [key for key in required if not cfg.get(key)]
    if missing:
        fail(f"{path.name}: missing keys {missing}")
        return
    recipient = str(cfg["recipient"]).strip()
    if "@" not in recipient or recipient.endswith((".",)):
        fail(f"{path.name}: recipient does not look like an email address")
    elif recipient.split("@", 1)[1] in ALLOWED_EMAIL_DOMAINS:
        if is_example:
            ok(f"{path.name} valid (placeholder recipient)")
        else:
            fail(f"{path.name}: replace the placeholder recipient before sending")
    else:
        ok(f"{path.name} valid (recipient set)")
    mode = (cfg.get("delivery") or {}).get("mode")
    if mode not in {"dsh_tool", "smtp", "none"}:
        fail(f"{path.name}: delivery.mode must be dsh_tool, smtp or none (got {mode!r})")
    else:
        ok(f"{path.name} delivery.mode={mode}")
    for key in ("handbook", "watchlist", "template"):
        value = cfg.get(key)
        if not value:
            warn(f"{path.name}: {key} is empty, fallback to bundled references/")
            continue
        resolved = Path(value).expanduser()
        if not resolved.is_absolute():
            resolved = ROOT / resolved
        if not resolved.is_file():
            fail(f"{path.name}: {key} does not exist: {value}")
        else:
            ok(f"{path.name} {key} -> {resolved}")


def check_python() -> None:
    for rel in ("scripts/md2docx.py", "scripts/send_email.py", "scripts/validate.py", "scripts/install.sh"):
        path = ROOT / rel
        if not path.is_file():
            continue
        if rel.endswith(".sh"):
            result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
            if result.returncode == 0:
                ok(f"{rel} syntax")
            else:
                fail(f"{rel} syntax: {result.stderr.strip()}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            ok(f"{rel} compiles")
        except py_compile.PyCompileError as exc:
            fail(f"{rel} does not compile: {exc.msg}")


def check_docx_smoke() -> None:
    converter = ROOT / "scripts/md2docx.py"
    source = ROOT / "references/report-template.md"
    if not converter.is_file() or not source.is_file():
        return
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "smoke.docx"
        result = subprocess.run(
            [sys.executable, str(converter), str(source), str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            fail(f"md2docx.py failed: {result.stderr.strip()}")
            return
        try:
            with zipfile.ZipFile(target) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile as exc:
            fail(f"md2docx.py produced an invalid zip: {exc}")
            return
        if "word/document.xml" not in names:
            fail("md2docx.py output has no word/document.xml")
        elif target.stat().st_size < 1024:
            fail("md2docx.py output is suspiciously small")
        else:
            ok(f"md2docx.py smoke test ({target.stat().st_size} bytes)")


def iter_text_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = set(path.relative_to(ROOT).parts)
        if rel_parts & SKIP_DIRS:
            continue
        if path.name in SKIP_FILES:
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def check_secrets() -> None:
    hits = 0
    for path, text in iter_text_files():
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    value = match.group(0)
                    if label == "email address" and value.split("@")[-1].lower() in ALLOWED_EMAIL_DOMAINS:
                        continue
                    hits += 1
                    fail(f"possible {label} in {path.relative_to(ROOT)}:{lineno}: {value!r}")
    if hits == 0:
        ok("no secrets / personal paths / private emails found")


def check_personal_config() -> None:
    config = ROOT / "config.json"
    example = ROOT / "config.example.json"
    check_json_config(example, is_example=True)
    if config.is_file():
        check_json_config(config, is_example=False)
        report_dir = Path(str(json.loads(config.read_text(encoding="utf-8"))["report_dir"])).expanduser()
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
            probe = report_dir / ".write-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            ok(f"report_dir writable: {report_dir}")
        except OSError as exc:
            fail(f"report_dir is not writable: {report_dir} ({exc})")
    else:
        warn("config.json not found — copy config.example.json and fill it in before the first run")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the morning-brief skill repository.")
    parser.add_argument("--repo-only", action="store_true", help="skip local config checks (CI mode)")
    args = parser.parse_args()

    print(f"repo: {ROOT}")
    for rel in REQUIRED_FILES + REQUIRED_REFERENCES + REQUIRED_SCRIPTS:
        check_file(rel)

    check_skill_frontmatter()
    check_python()
    check_docx_smoke()
    check_secrets()

    if not args.repo_only:
        check_personal_config()
    else:
        example = ROOT / "config.example.json"
        if example.is_file():
            try:
                json.loads(example.read_text(encoding="utf-8"))
                ok("config.example.json parses")
            except json.JSONDecodeError as exc:
                fail(f"config.example.json: {exc}")

    print()
    if failures:
        print(f"{len(failures)} failure(s), {len(warnings)} warning(s)")
        return 1
    print(f"all checks passed ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
