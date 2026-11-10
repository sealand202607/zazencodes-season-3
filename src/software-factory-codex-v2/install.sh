#!/usr/bin/env bash
# Copy the Codex factory template into a Git checkout. Run from any directory.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo "Usage: $0 /path/to/target-repo" >&2
  exit 2
fi
src=$(cd "$(dirname "$0")" && pwd -P)
target=$(git -C "$1" rev-parse --show-toplevel)
cd "$src"
files=(.agents/skills/factory/SKILL.md .codex/agents/factory_*.toml
       factory/config.json factory/checks.sh factory/bin/{job,gate,route}
       factory/dashboard.html factory/LICENSE)
for file in "${files[@]}"; do
  if [[ -e "$target/$file" || -L "$target/$file" ]]; then
    echo "Already exists: $target/$file. Review the existing installation before copying." >&2
    exit 1
  fi
done
for file in "${files[@]}"; do
  mkdir -p "$target/$(dirname "$file")"
  input=$file
  if [[ $file == factory/LICENSE ]]; then input=LICENSE; fi
  cp -p "$input" "$target/$file"
done
for entry in /factory/jobs/ /.worktrees/; do
  if ! grep -Fqx -- "$entry" "$target/.gitignore" 2>/dev/null; then
    printf '\n%s\n' "$entry" >> "$target/.gitignore"
  fi
done
echo "Copied factory to $target. Follow INSTALL.md to configure checks, labels and the base branch."
