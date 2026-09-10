#!/usr/bin/env python3
"""Builds a client-facing PDF report: clean prose and charts only, no
code, file paths, column/variable names, or other internal-project
references — a genuinely different document from the full-detail
notebook exports scripts/export_notebook_pdfs.sh produces, not the same
content with formatting layered on. "Boudica" branding, turquoise
accent, per the pattern requested 2026-09-10.

Takes a markdown "report body" file (written separately, by hand, for
each report -- this script does not attempt to auto-derive clean prose
from a notebook's own internal-facing commentary) plus chart images,
renders markdown -> HTML via python-markdown, wraps in
scripts/report_template.html, and prints to PDF via headless Chrome
(same engine export_notebook_pdfs.sh uses -- no new dependency).

Usage:
    python scripts/build_client_report.py \\
        --title "Report Title" \\
        --meta "10 September 2026" \\
        --body reports/foo.md \\
        --output pdf_outputs/foo.pdf

"Boudica report" is this project's own name for a PDF built this way --
when a request uses that phrase, this is the script and template it means
(see CLAUDE.md).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "scripts" / "report_template.html"

CHROME_CANDIDATES = ["google-chrome", "chromium", "chromium-browser"]
FALLBACK_CHROME = "/opt/google/chrome/chrome"


def find_chrome() -> str:
    for name in CHROME_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    if Path(FALLBACK_CHROME).is_file():
        return FALLBACK_CHROME
    print("[error] no Chrome/Chromium binary found", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--title", required=True)
    parser.add_argument("--kicker", default="RESEARCH NOTE")
    parser.add_argument("--meta", default="")
    parser.add_argument("--footer", default="Prepared by Boudica. Confidential — not for external distribution.")
    parser.add_argument("--body", required=True, type=Path, help="markdown file with the report's clean prose content")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    body_md = args.body.read_text()
    body_html = markdown.markdown(body_md, extensions=["extra", "sane_lists"])

    # Relative image paths in the markdown are resolved against the
    # markdown file's own directory and rewritten to absolute file paths
    # -- simpler and less fragile than a temp-dir symlink dance, and
    # correct regardless of where the HTML happens to be rendered from.
    body_dir = args.body.resolve().parent

    def _resolve_src(match: re.Match) -> str:
        src = match.group(1)
        if src.startswith(("http://", "https://", "/", "data:")):
            return match.group(0)
        return f'src="{(body_dir / src).resolve()}"'

    body_html = re.sub(r'src="([^"]+)"', _resolve_src, body_html)

    template = TEMPLATE_PATH.read_text()
    html = (
        template
        .replace("{{TITLE}}", args.title)
        .replace("{{KICKER}}", args.kicker)
        .replace("{{META}}", args.meta)
        .replace("{{FOOTER}}", args.footer)
        .replace("{{BODY}}", body_html)
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_html = Path(tmpdir) / "report.html"
        tmp_html.write_text(html)

        chrome = find_chrome()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                f"--print-to-pdf={args.output.resolve()}",
                f"file://{tmp_html}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    print(f"[ok] {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
