#!/usr/bin/env bash
set -euo pipefail
# Official release, pinned to the version used by this project's acceptance checks.
PAC_HUGO_VERSION=0.168.0
PAC_TOOL_DIR="${RUNNER_TEMP:-/tmp}/pac-hugo"
mkdir -p "$PAC_TOOL_DIR"
curl --fail --silent --show-error --location "https://github.com/gohugoio/hugo/releases/download/v${PAC_HUGO_VERSION}/hugo_extended_${PAC_HUGO_VERSION}_linux-amd64.tar.gz" -o "$PAC_TOOL_DIR/hugo.tar.gz"
curl --fail --silent --show-error --location "https://github.com/gohugoio/hugo/releases/download/v${PAC_HUGO_VERSION}/hugo_${PAC_HUGO_VERSION}_checksums.txt" -o "$PAC_TOOL_DIR/checksums.txt"
python3 - "$PAC_TOOL_DIR" "$PAC_HUGO_VERSION" <<'PY'
from hashlib import sha256
from pathlib import Path
import sys
p=Path(sys.argv[1]); name=f'hugo_extended_{sys.argv[2]}_linux-amd64.tar.gz'
expected=next(line.split()[0] for line in (p/'checksums.txt').read_text().splitlines() if line.split()[-1]==name)
assert sha256((p/'hugo.tar.gz').read_bytes()).hexdigest()==expected, 'Hugo checksum mismatch'
PY
tar -xzf "$PAC_TOOL_DIR/hugo.tar.gz" -C "$PAC_TOOL_DIR" hugo
if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "$PAC_TOOL_DIR" >> "$GITHUB_PATH"
fi
"$PAC_TOOL_DIR/hugo" version
