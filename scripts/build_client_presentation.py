#!/usr/bin/env python3
"""Builds a "Boudica presentation" -- a landscape, slide-deck-format PDF,
one declarative headline per slide with a single large chart doing the
demonstrating (the Matthew Ball "State of ..." deck pattern, adopted
2026-09-11 as a second Boudica format alongside the portrait report
format scripts/build_client_report.py builds).

Mirrors that script's own separation of engine vs. content: a slide deck
is defined in presentations/<name>/deck.yaml (hand-authored, references
chart images under presentations/<name>/figs/) and rendered through
scripts/presentation_template.html via the same headless-Chrome
print-to-pdf engine every other PDF pipeline in this project uses.

deck.yaml shape:
    kicker: "Research Note · Presentation"
    title: "Deck Title"
    subtitle: "One-line framing."
    date: "11 September 2026"
    deck_label: "Running header shown on every content slide"
    slides:
      - type: section
        numeral: "I."
        heading: "Section Heading"
      - type: content
        headline: "The one-sentence claim this slide demonstrates."
        image: figs/some_chart.png
        note: "Optional small caption/source line under the chart."
      - type: closing
        heading: "Sources"
        items:
          - "**Label.** Description in plain language."

Usage:
    python scripts/build_client_presentation.py \\
        --deck presentations/state_of_cs/deck.yaml \\
        --output pdf_outputs/state_of_cs.pdf
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "scripts" / "presentation_template.html"

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


def _bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def render_title(deck: dict) -> str:
    return f"""
<div class="slide title">
  <div class="mark">BOUDICA</div>
  <div class="kicker">{deck.get("kicker", "Research Note")}</div>
  <h1>{deck["title"]}</h1>
  <div class="subtitle">{deck.get("subtitle", "")}</div>
  <div class="rule"></div>
  <div class="meta">{deck.get("date", "")}</div>
</div>"""


def render_section(slide: dict) -> str:
    return f"""
<div class="slide section">
  <div class="mark">BOUDICA</div>
  <div class="num">{slide.get("numeral", "")}</div>
  <h1>{slide["heading"]}</h1>
</div>"""


def render_content(slide: dict, deck_label: str, body_dir: Path, page_no: int) -> str:
    img_src = (body_dir / slide["image"]).resolve()
    note = f'<div class="note">{slide["note"]}</div>' if slide.get("note") else ""
    return f"""
<div class="slide content">
  <div class="mark">BOUDICA</div>
  <div class="deck-kicker">{deck_label}</div>
  <h2>{slide["headline"]}</h2>
  <div class="chart-wrap"><img src="file://{img_src}"></div>
  {note}
  <div class="pagenum">{page_no}</div>
</div>"""


def render_closing(slide: dict) -> str:
    items = "".join(f"<li>{_bold(item)}</li>" for item in slide.get("items", []))
    return f"""
<div class="slide closing">
  <div class="mark">BOUDICA</div>
  <h2>{slide["heading"]}</h2>
  <ul>{items}</ul>
</div>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deck", required=True, type=Path, help="path to deck.yaml")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    deck = yaml.safe_load(args.deck.read_text())
    body_dir = args.deck.resolve().parent
    deck_label = deck.get("deck_label", deck.get("title", ""))

    parts = [render_title(deck)]
    page_no = 2
    for slide in deck.get("slides", []):
        kind = slide["type"]
        if kind == "section":
            parts.append(render_section(slide))
        elif kind == "content":
            parts.append(render_content(slide, deck_label, body_dir, page_no))
        elif kind == "closing":
            parts.append(render_closing(slide))
        else:
            print(f"[error] unknown slide type: {kind}", file=sys.stderr)
            return 1
        page_no += 1

    template = TEMPLATE_PATH.read_text()
    fontfaces = ""
    # Reuse the same embedded @font-face blocks the report template uses,
    # rather than re-fetching -- same fonts, same reasoning (CLAUDE.md's
    # boudica-report section).
    report_template = (REPO_ROOT / "scripts" / "report_template.html").read_text()
    matches = re.findall(r"@font-face \{.*?\}\n", report_template, re.DOTALL)
    fontfaces = "".join(matches)

    html = template.replace("/* __FONT_FACES__ */", fontfaces).replace("__SLIDES__", "\n".join(parts))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_html = Path(tmpdir) / "deck.html"
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

    print(f"[ok] {args.output} ({len(deck.get('slides', [])) + 1} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
