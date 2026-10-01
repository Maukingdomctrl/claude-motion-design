#!/bin/bash
# Installs the motion-design skill and its Python deps in Claude Code on the web sessions.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# 1. Skill: refresh the copy in ~/.claude/skills from the repo so edits on the branch are picked up.
mkdir -p "$HOME/.claude/skills"
rm -rf "$HOME/.claude/skills/motion-design"
cp -r "$REPO/skill/motion-design" "$HOME/.claude/skills/"

# 2. Python deps. Playwright 1.56.0 drives Chromium build 1194, which the web container preinstalls
#    under $PLAYWRIGHT_BROWSERS_PATH, so no browser download is needed.
pip install -q --disable-pip-version-check --root-user-action=ignore \
  "playwright==1.56.0" imageio-ffmpeg numpy pillow

# 3. Fallback: only download Chromium if the matching build is missing.
if [ ! -d "${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}/chromium-1194" ]; then
  python3 -m playwright install chromium
fi
