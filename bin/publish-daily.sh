#!/bin/sh
set -eu

REPO=/home/hackrf/signals
SPOOL=/home/hackrf/signal-spool
LOCK=/run/lock/hackrf-signal-publish.lock

exec 9>"$LOCK"
flock -n 9 || exit 0

cd "$REPO"
today="$(date -u +%Y-%m-%d)"

# A network or GitHub failure exits without touching the spool. The next timer
# run starts with the oldest completed day, so an offline backlog drains in
# order once connectivity returns.
git fetch origin

queue="$(mktemp)"
trap 'rm -f -- "$queue"' EXIT HUP INT TERM
find "$SPOOL/data" -type f -name '*.jsonl' ! -name "${today}.jsonl" -print 2>/dev/null | sort >"$queue"

while IFS= read -r source; do
    relative="${source#"$SPOOL/"}"
    day="$(basename "$source" .jsonl)"
    local_hash="$(sha256sum "$source" | awk '{print $1}')"

    git fetch origin
    if git cat-file -e "origin/main:$relative" 2>/dev/null; then
        remote_hash="$(git show "origin/main:$relative" | sha256sum | awk '{print $1}')"
        if [ "$remote_hash" = "$local_hash" ]; then
            rm -f -- "$source"
            continue
        fi
        echo "Refusing to overwrite different data already on main: $relative" >&2
        exit 1
    fi

    branch="archive/${day}-${local_hash%${local_hash#????????????}}"
    if git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
        git switch -C "$branch" "origin/$branch"
    else
        git switch -C "$branch" origin/main
    fi

    mkdir -p "$(dirname "$relative")"
    cp -- "$source" "$relative"
    git add -- "$relative"
    if ! git diff --cached --quiet; then
        git commit -m "Add signal log for $day"
    fi
    git push -u origin "$branch"

    pr="$(gh pr list --repo ufo-files/signals --head "$branch" --state open --json number --jq '.[0].number // empty')"
    if [ -z "$pr" ]; then
        pr="$(gh pr create --repo ufo-files/signals --base main --head "$branch" \
            --title "Add signal log for $day" \
            --body "Automated UTC HackRF spectrum archive for $day." | sed 's#.*/##')"
    fi
    gh pr merge "$pr" --repo ufo-files/signals --merge --delete-branch

    git fetch origin
    remote_hash="$(git show "origin/main:$relative" | sha256sum | awk '{print $1}')"
    if [ "$remote_hash" != "$local_hash" ]; then
        echo "Merge verification failed for $relative; retaining local file" >&2
        exit 1
    fi

    rm -f -- "$source"
done <"$queue"

find "$SPOOL/data" -depth -type d -empty -delete 2>/dev/null || true
git switch main
git pull --ff-only origin main
