#!/usr/bin/env python3
"""Build module_summary.pdf from module_summary.md (Chrome headless) and verify it.

Run from the repo root (or anywhere; paths resolve from this file):

    .venv\\Scripts\\python.exe build\\build_report.py

Exit 0 only when every gate passes; exit 1 prints each failing gate.
The script never writes module_summary.md.

Ported from MS-09-CAP-04-AML build/build_report.py; the constants are the
DLS ones (title, nine section bookmarks, date line, pinned values from
test-runs/2026-11-06-runall.txt) and the rendering CSS is identical, so the
PDF matches the previous capstone's look.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "module_summary.md"
PDF = ROOT / "module_summary.pdf"
OUT_DIR = ROOT / "build" / "out"
HTML = OUT_DIR / "report.html"
PREV_PDF = ROOT / "test-runs" / "module_summary.previous.pdf"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

HEADINGS = (
    "Overview",
    "Dataset and Task Description",
    "Model Architecture and Design Decisions",
    "Experimental Comparison",
    "Results and Interpretation",
    "Interpretation for a Non-Technical Audience",
    "Limitations and Risks",
    "Ethical and Responsible Use",
    "References",
)

DATE_LINE = "2026-11-05"
COVER_FIELDS = ("Author:", "Dataset:", "Project:", "Date:")
TITLE = "Deep Learning Systems Analysis Report - Cat and Dog Breed Classification"
AUTHOR = "Francisco Mateus"

# Pinned values from test-runs/2026-11-06-runall.txt (fresh-run authority),
# as they appear in module_summary.md.
PINNED = (
    ("7,349", "total photographs"),
    ("3,680", "trainval pool"),
    ("3,669", "test set"),
    ("3,129", "training images"),
    ("551", "validation images"),
    ("93 to 100", "images per breed in trainval"),
    ("0.2044", "baseline test accuracy"),
    ("0.2051", "baseline macro per-class accuracy"),
    ("0.8940", "ResNet18 test accuracy"),
    ("0.8934", "ResNet18 macro per-class accuracy"),
    ("0.6896", "accuracy difference"),
    ("389", "ResNet18 misclassified test images"),
    ("2.7%", "random-guess accuracy"),
    ("2.5792", "baseline best validation loss"),
    ("27", "baseline best epoch"),
    ("0.2321", "ResNet18 best validation loss"),
    ("8", "ResNet18 best epoch"),
    ("13", "ResNet18 stop epoch"),
    ("30", "baseline epochs completed"),
    ("0.4203", "baseline final training accuracy"),
    ("0.2813", "baseline final validation accuracy"),
    ("0.1390", "baseline train-validation gap"),
    ("0.0726", "ResNet18 train-validation gap"),
    ("0.9274", "ResNet18 final validation accuracy"),
    ("1.0000", "ResNet18 final training accuracy"),
    ("1e-4", "pretrained backbone learning rate"),
    ("1e-3", "new head learning rate"),
    ("224 by 224", "input size"),
)

IMAGE_COUNT = 2
MIN_PAGES = 6
MAX_PAGES = 16

CSS = """
@page {
  size: letter;
  margin: 0.9in;
  @bottom-right {
    content: counter(page);
    font-family: "Times New Roman", Times, serif;
    font-size: 10px;
    color: #000;
  }
}
body {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 16px;
  line-height: 1.5;
  color: #000;
  margin: 0;
  overflow-wrap: break-word;
}
.cover {
  page-break-after: always;
  break-after: page;
  text-align: center;
  padding-top: 1.5in;
}
.cover h1 {
  font-size: 26.7px;
  line-height: 1.3;
  margin: 0 0 1.6em;
}
.cover p {
  margin: 0.15em 0;
  font-size: 16px;
}
h2 {
  font-size: 21.3px;
  margin: 1.5em 0 0.6em;
  page-break-after: avoid;
  break-after: avoid;
}
h3 {
  font-size: 18px;
  margin: 1.2em 0 0.4em;
  page-break-after: avoid;
  break-after: avoid;
}
h2.new-page {
  page-break-before: always;
  break-before: page;
}
p { margin: 0 0 0.75em; orphans: 3; widows: 3; }
p:has(+ ul), p:has(+ ol), p:has(+ table) {
  page-break-after: avoid;
  break-after: avoid;
}
ul, ol { margin: 0.4em 0 0.9em 1.5em; padding: 0; page-break-inside: avoid; break-inside: avoid; }
li { margin-bottom: 0.25em; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5em 0 1em;
  font-size: 14.7px;
  page-break-inside: avoid;
  break-inside: avoid;
}
th, td {
  border: 1px solid #555;
  padding: 0.25em 0.5em;
  text-align: left;
}
th { background: #eeeeee; }
figure {
  margin: 1em 0;
  page-break-inside: avoid;
  break-inside: avoid;
  text-align: center;
}
figure img {
  max-width: 100%;
  height: auto;
}
figcaption {
  font-size: 14.7px;
  margin-top: 0.4em;
  text-align: left;
}
"""

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Deep Learning Systems Analysis Report - Cat and Dog Breed Classification</title>
<style>
{css}
</style>
</head>
<body>
{body}
</body>
</html>
"""

# An image paragraph followed by its bold "Figure N." caption becomes one
# <figure> block, so a page break can never separate the two.
FIGURE_RE = re.compile(
    r"<p>(<img\b[^>]*>)</p>\s*<p>(<strong>Figure \d+\.</strong>.*?)</p>",
    re.S,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(lines: list[str]) -> int:
    for line in lines:
        print(f"FAIL {line}")
    return 1


def absolutize_images(html_text: str) -> str:
    """Point every <img src> at an absolute file:/// URI; a missing figure fails."""
    def repl(match: re.Match[str]) -> str:
        src = match.group(1)
        target = (ROOT / src).resolve()
        if not target.is_file():
            raise SystemExit(f"FAIL figure not found: {src} -> {target}")
        return f'src="{target.as_uri()}"'

    return re.sub(r'src="([^"]+)"', repl, html_text)


def wrap_figures(html_text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"<figure>{match.group(1)}<figcaption>{match.group(2)}</figcaption></figure>"

    return FIGURE_RE.sub(repl, html_text)


def split_cover(html_text: str) -> str:
    """Everything before the first h2 is the cover page; the rest is the body."""
    index = html_text.find("<h2")
    if index == -1:
        raise SystemExit("FAIL no <h2> section heading found")
    cover, body = html_text[:index], html_text[index:]
    return f'<section class="cover">{cover}</section>\n{body}'


def has_page_number(page, number: int) -> bool:
    """True when the page's bottom margin carries its own page number."""
    content_height = float(page.mediabox.height) * 96 / 72
    found = False

    def visit(text, cm, tm, font_dict, font_size):
        nonlocal found
        if text.strip() == str(number) and tm[5] > 0.9 * content_height:
            found = True

    page.extract_text(visitor_text=visit)
    return found


def heading_pages(reader: PdfReader) -> dict[str, int]:
    """Page index for each section heading, scanned in document order."""
    page_for: dict[str, int] = {}
    start = 0
    for heading in HEADINGS:
        for index in range(start, len(reader.pages)):
            flat = re.sub(r"\s+", " ", reader.pages[index].extract_text() or "")
            if heading in flat:
                page_for[heading] = index
                start = index
                break
    return page_for


def add_outline_and_metadata() -> None:
    """Add the nine section bookmarks and the title/author metadata."""
    reader = PdfReader(str(PDF))
    page_for = heading_pages(reader)
    missing = [h for h in HEADINGS if h not in page_for]
    if missing:
        raise SystemExit(f"FAIL bookmark target not found: {missing}")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": TITLE, "/Author": AUTHOR})
    for heading in HEADINGS:
        writer.add_outline_item(heading, page_for[heading])

    temp = OUT_DIR / "module_summary.outline.pdf"
    with open(temp, "wb") as handle:
        writer.write(handle)
    temp.replace(PDF)


def main() -> int:
    if not MD.is_file():
        return fail([f"source missing: {MD}"])
    if not CHROME.is_file():
        return fail([f"chrome missing: {CHROME}"])

    md_hash_before = sha256(MD)
    html_text = markdown.markdown(
        MD.read_text(encoding="utf-8"), extensions=["extra", "sane_lists"]
    )
    html_text = absolutize_images(html_text)
    html_text = wrap_figures(html_text)
    html_text = split_cover(html_text)
    # References get their own page (owner decision, 2026-11-06).
    html_text = html_text.replace("<h2>References</h2>", '<h2 class="new-page">References</h2>', 1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML.write_text(TEMPLATE.format(css=CSS, body=html_text), encoding="utf-8")

    if PDF.exists():
        PREV_PDF.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PDF, PREV_PDF)
        PDF.unlink()

    cmd = [
        str(CHROME),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF}",
        HTML.as_uri(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return fail([f"chrome exit {proc.returncode}", (proc.stderr or "").strip()[:500]])
    if not PDF.is_file():
        return fail(["chrome reported success but wrote no PDF"])
    if PDF.stat().st_size == 0:
        return fail(["PDF is empty"])
    if PDF.read_bytes()[:4] != b"%PDF":
        return fail(["PDF does not start with %PDF"])

    add_outline_and_metadata()

    reader = PdfReader(str(PDF))
    problems: list[str] = []
    texts: list[str] = []
    image_count = 0
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        texts.append(text)
        page_images = len(page.images)
        image_count += page_images
        if not text.strip() and page_images == 0:
            problems.append(f"blank page {number}")
        if not has_page_number(page, number):
            problems.append(f"page number missing on page {number}")

    flat = re.sub(r"\s+", " ", "\n".join(texts))

    cover_text = texts[0] if texts else ""
    for field in COVER_FIELDS:
        if field not in cover_text:
            problems.append(f"cover field missing: {field}")
    if "Overview" in cover_text:
        problems.append("cover page contains body content (Overview)")

    for heading in HEADINGS:
        if heading not in flat:
            problems.append(f"heading missing: {heading}")
    if DATE_LINE not in flat:
        problems.append(f"date line missing: {DATE_LINE}")
    for value, label in PINNED:
        if value not in flat:
            problems.append(f"pinned value missing: {value} ({label})")
    if image_count != IMAGE_COUNT:
        problems.append(f"image count {image_count} != {IMAGE_COUNT}")

    # Each figure caption must sit on a page that carries an image.
    for number, page in enumerate(reader.pages, 1):
        text = texts[number - 1]
        for figure in ("Figure 1.", "Figure 2."):
            if figure in text and len(page.images) == 0:
                problems.append(f"{figure} caption on page {number} without its image")

    if not (MIN_PAGES <= len(reader.pages) <= MAX_PAGES):
        problems.append(f"page count {len(reader.pages)} out of {MIN_PAGES}-{MAX_PAGES}")

    outline = [item for item in reader.outline if not isinstance(item, list)]
    titles = [str(item.title) for item in outline]
    if titles != list(HEADINGS):
        problems.append(f"bookmarks mismatch: {titles}")
    else:
        expected = heading_pages(reader)
        for item in outline:
            if reader.get_destination_page_number(item) != expected.get(str(item.title)):
                problems.append(f"bookmark target wrong: {item.title}")

    metadata = reader.metadata or {}
    if (metadata.get("/Author") or "") != AUTHOR:
        problems.append("PDF author metadata missing")
    if "Cat and Dog Breed Classification" not in (metadata.get("/Title") or ""):
        problems.append("PDF title metadata missing")

    text = "\n".join(texts)
    if "`" in text:
        problems.append("literal backtick in extracted text")
    if "$" in text:
        problems.append("literal dollar sign in extracted text")
    if "\ufffd" in text:
        problems.append("U+FFFD replacement character in extracted text")

    md_hash_after = sha256(MD)
    if md_hash_after != md_hash_before:
        problems.append("source Markdown changed during the build")

    if problems:
        return fail(problems)

    print(f"PASS pages={len(reader.pages)} images={image_count} bookmarks={len(outline)} size={PDF.stat().st_size} bytes")
    print(f"pdf sha256={sha256(PDF)}")
    print(f"md  sha256={md_hash_after}  source md unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
