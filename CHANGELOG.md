# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-05

### Added

- `SKILL.md` entry point with trigger conditions and an eight-step procedure.
- `references/`: handbook (product-first rules), example watchlist, eight-chapter
  report template, output spec, and scheduling guide.
- `scripts/md2docx.py`: dependency-free Markdown → OOXML `.docx` converter.
- `scripts/send_email.py`: SMTP fallback sender with attachments and
  environment-variable passwords.
- `scripts/validate.py`: structure, frontmatter, docx smoke test and secret scan.
- `scripts/install.sh`: installer for user-level and project-level skill roots.
- `config.example.json` with configurable recipient, subject, report directory,
  rule-file paths and delivery mode.
- GitHub Actions workflow running the self-check on Python 3.9 and 3.12.
- Chinese and English READMEs, MIT license, `.gitignore` excluding private
  config and generated reports.
