#!/usr/bin/env bash
# Install the morning-brief skill into a DeepSeek Harness skill root.
set -euo pipefail

SKILL_NAME="morning-brief"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"

DEST=""
FORCE=0
CREATE_CONFIG=1

usage() {
  cat <<'EOF'
Install the morning-brief skill.

Usage:
  scripts/install.sh                     # user level:  ${DSH_HOME:-~/.dsh}/skills/morning-brief
  scripts/install.sh --project DIR       # project level: DIR/.dsh/skills/morning-brief
  scripts/install.sh --dest DIR          # explicit destination directory

Options:
  --force        replace an existing installation (previous one is backed up)
  --no-config    do not create config.json from config.example.json
  -h, --help     show this help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)
      [ $# -ge 2 ] || { echo "--project requires a directory" >&2; exit 2; }
      DEST="$2/.dsh/skills/$SKILL_NAME"
      shift 2
      ;;
    --dest)
      [ $# -ge 2 ] || { echo "--dest requires a directory" >&2; exit 2; }
      DEST="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --no-config)
      CREATE_CONFIG=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[ -f "$SRC_DIR/SKILL.md" ] || { echo "SKILL.md not found in $SRC_DIR" >&2; exit 1; }
[ -n "$DEST" ] || DEST="$DSH_HOME/skills/$SKILL_NAME"

if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null || true)" ]; then
  if [ "$FORCE" -ne 1 ]; then
    echo "destination already exists: $DEST" >&2
    echo "re-run with --force to replace it (a backup will be created)" >&2
    exit 1
  fi
  BACKUP="$DEST.bak.$(date +%Y%m%d-%H%M%S)"
  mv "$DEST" "$BACKUP"
  echo "existing installation backed up to: $BACKUP"
fi

mkdir -p "$DEST"
tar -C "$SRC_DIR" \
  --exclude='./.git' \
  --exclude='./.github' \
  --exclude='./config.json' \
  --exclude='./reports' \
  --exclude='./__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.docx' \
  -cf - . | tar -C "$DEST" -xf -
echo "installed to: $DEST"

if [ "$CREATE_CONFIG" -eq 1 ] && [ ! -f "$DEST/config.json" ] && [ -f "$DEST/config.example.json" ]; then
  cp "$DEST/config.example.json" "$DEST/config.json"
  echo "created config from example: $DEST/config.json"
fi

if [ -f "$DEST/config.json" ] && python3 - "$DEST/config.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    config = json.load(handle)
recipient = str(config.get("recipient") or "")
sys.exit(0 if recipient and not recipient.endswith("@example.com") else 1)
PY
then
  python3 "$DEST/scripts/validate.py"
else
  cat <<EOF

Next steps:
  1. edit $DEST/config.json  (at least: recipient)
  2. run: python3 $DEST/scripts/validate.py
EOF
fi
