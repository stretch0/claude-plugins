#!/usr/bin/env bash
# copy-env.sh: copy git-ignored env files from the main checkout into the
# current git worktree, so the app can start there.
#
# Usage: copy-env.sh [--overwrite] <path> [<path> ...]
#
# Each <path> is relative to the repository root and names either a
# directory or a single file:
#   .                  -> the root's .env and .env.* files
#   apps/web           -> apps/web/.env and apps/web/.env.* files
#   apps/web/.env.dev  -> just that file
#
# Files ending in .example, .sample or .template are skipped, because they
# are tracked templates rather than real config. Existing files in the
# worktree are kept unless --overwrite is given. The script prints file
# names only, never their contents.

set -euo pipefail

OVERWRITE=0
PATHS=()
for arg in "$@"; do
    case "$arg" in
        --overwrite) OVERWRITE=1 ;;
        -h | --help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) PATHS+=("$arg") ;;
    esac
done

if [[ ${#PATHS[@]} -eq 0 ]]; then
    echo "error: give at least one path, e.g. '.' or 'apps/web'" >&2
    exit 2
fi

DEST_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "error: not inside a git repository" >&2
    exit 2
}
# The first entry of `git worktree list` is always the main checkout.
SOURCE_ROOT=$(git worktree list --porcelain | awk '/^worktree /{print substr($0, 10); exit}')

if [[ "$SOURCE_ROOT" == "$DEST_ROOT" ]]; then
    echo "This is the main checkout, so its env files are already in place. Nothing to copy."
    exit 0
fi

is_template() {
    case "$1" in
        *.example | *.sample | *.template) return 0 ;;
        *) return 1 ;;
    esac
}

copied=0
copy_one() {
    local relative="$1"
    local from="$SOURCE_ROOT/$relative" to="$DEST_ROOT/$relative"
    if [[ -e "$to" && $OVERWRITE -eq 0 ]]; then
        echo "kept      $relative (already in the worktree; pass --overwrite to replace it)"
        return
    fi
    mkdir -p "$(dirname "$to")"
    cp -p "$from" "$to"
    echo "copied    $relative"
    copied=$((copied + 1))
}

for raw in "${PATHS[@]}"; do
    relative="${raw#./}"
    relative="${relative%/}"
    [[ -z "$relative" || "$relative" == "." ]] && relative="."
    case "/$relative/" in
        */../*)
            echo "error: '$raw' leaves the repository; use a path inside it" >&2
            exit 2
            ;;
    esac

    source_path="$SOURCE_ROOT/$relative"
    if [[ -f "$source_path" ]]; then
        copy_one "$relative"
    elif [[ -d "$source_path" ]]; then
        found=0
        for file in "$source_path"/.env "$source_path"/.env.*; do
            [[ -f "$file" ]] || continue
            name=$(basename "$file")
            is_template "$name" && continue
            found=1
            if [[ "$relative" == "." ]]; then copy_one "$name"; else copy_one "$relative/$name"; fi
        done
        [[ $found -eq 1 ]] || echo "none      no .env files in $relative of the main checkout ($SOURCE_ROOT)"
    else
        echo "missing   $relative does not exist in the main checkout ($SOURCE_ROOT)"
    fi
done

echo "Done: $copied file(s) copied from $SOURCE_ROOT into $DEST_ROOT."
