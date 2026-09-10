#!/usr/bin/env bash
# Exports one or more notebooks to presentation-ready PDFs under
# pdf_outputs/ -- commentary and chart/table outputs only, no source code
# (jupyter nbconvert --no-input), rendered via the system's installed
# Chrome in headless mode (no LaTeX/wkhtmltopdf/playwright dependency).
#
# Usage:
#   scripts/export_notebook_pdfs.sh notebooks/foo.ipynb notebooks/bar.ipynb
#   scripts/export_notebook_pdfs.sh notebooks/*.ipynb
#
# Requires: jupyter nbconvert (already in requirements.txt) and a Chrome/
# Chromium binary on PATH or at one of the common install locations below.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_ROOT/pdf_outputs"
TMP_HTML_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_HTML_DIR"' EXIT

CHROME_BIN="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
if [ -z "$CHROME_BIN" ] && [ -x /opt/google/chrome/chrome ]; then
  CHROME_BIN="/opt/google/chrome/chrome"
fi
if [ -z "$CHROME_BIN" ]; then
  echo "[error] no Chrome/Chromium binary found -- install one, or set CHROME_BIN explicitly" >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 <notebook.ipynb> [more.ipynb ...]" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

for nb in "$@"; do
  name="$(basename "$nb" .ipynb)"
  echo "[info] $name: notebook -> html (no code input)"
  jupyter nbconvert --to html --no-input --output-dir "$TMP_HTML_DIR" "$nb"

  echo "[info] $name: html -> pdf (headless Chrome)"
  "$CHROME_BIN" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf="$OUT_DIR/$name.pdf" \
    "file://$TMP_HTML_DIR/$name.html" >/dev/null 2>&1

  echo "[ok] $OUT_DIR/$name.pdf"
done
