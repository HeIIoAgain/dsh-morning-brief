# dsh-morning-brief

> A reusable agent skill for a **daily semiconductor-industry morning brief**: it turns overnight product/technology news into an A-share / HK-stock impact report, renders a Word (`.docx`) deep-dive and delivers both by email.

[![CI](https://github.com/HeIIoAgain/dsh-morning-brief/actions/workflows/ci.yml/badge.svg)](https://github.com/HeIIoAgain/dsh-morning-brief/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

## What it does

Every morning (default 05:00 Asia/Shanghai) the agent searches public sources for semiconductor product/technology news from the previous 24 hours, judges the transmission to listed companies, and produces:

| Output | Content |
|---|---|
| Email body | Condensed brief: 3–5 product items (200–300 Chinese chars each) + consensus/divergence/new-variable views + A-share mapping table |
| Word attachment | Eight-chapter deep dive: product & process progress tables, A-share mapping, event calendar, risks and invalidation signals, 12 dated sources |
| Local files | Deliberately deleted after a successful send (`reports/` is a temp workspace only) |

The repo ships the **judgement rules, search templates and delivery pipeline**; the actual search and writing are done by the agent.

## Quick start

```bash
git clone https://github.com/<your-name>/dsh-morning-brief.git
mkdir -p ~/.dsh/skills
cp -R dsh-morning-brief ~/.dsh/skills/morning-brief
cd ~/.dsh/skills/morning-brief

cp config.example.json config.json
$EDITOR config.json            # at least set recipient
python3 scripts/validate.py    # should pass
```

Then ask the agent to "run the morning brief" (「跑一份晨报」). For a project-scoped install, copy the folder to `<project>/.dsh/skills/` or run `./scripts/install.sh --project .`.

Without DeepSeek Harness the rules still apply; use the bundled tools directly:

```bash
python3 scripts/md2docx.py references/report-template.md out.docx
export MORNING_BRIEF_SMTP_PASSWORD='app-password'
python3 scripts/send_email.py --config config.json \
  --subject "Semiconductor Brief · 2026-10-09" \
  --body-file body.txt --attach out.docx
```

## Configuration

`config.example.json` → `config.json` (gitignored). Key fields: `recipient`, `subject`, `docx_basename`, `report_dir`, `timezone`, `window_start`, and paths to the replaceable rule files (`handbook`, `watchlist`, `template`). Delivery is `dsh_tool` (default), `smtp` or `none`. SMTP passwords are read from the environment variable named by `password_env` — never stored in the file.

## Scheduling

The skill does not schedule itself. With DSH, create a daily reminder:

```python
schedule_create(
    daily={"time": "05:00:00", "time_zone": "Asia/Shanghai"},
    title="Semiconductor morning brief",
    prompt="Run today's morning brief: load the morning-brief skill and follow it end to end.",
)
```

Missed reminders are delivered once (latest occurrence only) after the host restarts. Manual runs are always available and always re-search.

## Repository layout

```text
SKILL.md                  # entry point: triggers + procedure
config.example.json       # configuration template
references/               # handbook, watchlist, report template, output spec, schedule
scripts/                  # md2docx.py, send_email.py, validate.py, install.sh
.github/workflows/        # CI: structure, frontmatter, docx smoke test, secret scan
```

## Quality rules

Product-level facts only (model/node/spec/customer/date), every fact carries a source link and publish time, facts vs. forecasts vs. rumours are separated, no invented numbers or ticker codes, and a non-investment-advice disclaimer is always appended.

## Security

No personal email addresses, credentials or absolute local paths are committed; CI scans for common leak patterns. `config.json` is gitignored and SMTP secrets come from environment variables.

## Disclaimer

This project organizes public information for research assistance. It is **not investment advice**. Markets carry risk; verify any number or ticker before trading.

## License

[MIT](LICENSE) © 2026 dsh-morning-brief contributors
