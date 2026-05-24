#!/usr/bin/env bash
# Build & publish aiedu notes.
# Usage: ./publish.sh ["custom commit message"]
set -euo pipefail
cd "$(dirname "$0")"

python3 build.py

if [[ -z "$(git status --porcelain)" ]]; then
  echo "[publish] no changes."
  exit 0
fi

msg="${1:-update notes ($(date +%Y-%m-%d))}"
git add -A
git -c commit.gpgsign=false commit -m "$msg"
git push
echo "[publish] pushed: $msg"
echo "[publish] live at https://letranger.github.io/aiedu/"
