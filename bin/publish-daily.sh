#!/bin/sh
set -eu

REPO=/home/hackrf/signals
LOCK=/run/lock/hackrf-signal-publish.lock

exec 9>"$LOCK"
flock -n 9 || exit 0

cd "$REPO"
git fetch origin main
git switch main
git pull --ff-only origin main

# Publish only completed UTC days; today's file remains local and mutable.
today="$(date -u +%Y-%m-%d)"
find data -type f -name '*.jsonl' ! -name "${today}.jsonl" -print 2>/dev/null |
while IFS= read -r path; do
    git add -- "$path"
done

if git diff --cached --quiet; then
    exit 0
fi

git commit -m "Add signal logs through $(date -u -d yesterday +%Y-%m-%d)"
git push origin main
