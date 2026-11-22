#!/usr/bin/env bash
# Render diagrams/src/*.mmd to diagrams/rendered/*.svg (needs Node and @mermaid-js/mermaid-cli).
#   npm install -g @mermaid-js/mermaid-cli     # provides `mmdc`
#   bash diagrams/render.sh
set -euo pipefail
cd "$(dirname "$0")"
command -v mmdc >/dev/null || { echo "mmdc not found: npm install -g @mermaid-js/mermaid-cli" >&2; exit 1; }
mkdir -p rendered
fail=0
for src in src/*.mmd; do
  name="$(basename "${src%.mmd}")"
  if mmdc -q -i "$src" -o "rendered/${name}.svg" -b transparent; then
    echo "ok   ${name}.svg"
  else
    echo "FAIL ${name}" >&2; fail=1
  fi
done
exit "$fail"
