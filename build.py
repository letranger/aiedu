#!/usr/bin/env python3
"""Build static site for aiedu paper notes.

Workflow:
  1. Each paper lives in papers_src/<slug>.org with metadata as #+KEYWORD lines.
  2. emacs --batch exports body to HTML fragment.
  3. We wrap fragment with paper.html template -> p/<slug>.html
  4. Cards (sorted by DATE desc) injected into index.html template.

Required org keywords per paper:
  #+TITLE: 中文標題
  #+ORIGINAL_TITLE: English title
  #+AUTHORS: A, B, C
  #+JOURNAL: name
  #+JOURNAL_URL: (optional)
  #+YEAR: 2024
  #+DATE: 2026-05-24            ; date the note was written
  #+ABSTRACT: one-paragraph hook used on card + detail page
  #+LINK: (optional) paper download/landing URL
  #+PDF:  (optional) local relative path to pdf
"""
from __future__ import annotations
import html
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
SRC_DIR = ROOT / "papers_src"
OUT_DIR = ROOT / "p"
TEMPLATES = ROOT / "templates"

META_KEYS = {
    "TITLE", "ORIGINAL_TITLE", "AUTHORS",
    "JOURNAL", "JOURNAL_URL", "YEAR",
    "DATE", "ABSTRACT", "LINK", "PDF",
}

META_RE = re.compile(r"^#\+([A-Z_]+):\s*(.*)$")


def parse_org(path: Path) -> tuple[dict, str]:
    """Return (metadata dict, body org-source without metadata)."""
    meta: dict[str, str] = {}
    body_lines: list[str] = []
    in_body = False
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not in_body:
                m = META_RE.match(line.rstrip("\n"))
                if m and m.group(1) in META_KEYS:
                    meta[m.group(1)] = m.group(2).strip()
                    continue
                if line.strip() == "":
                    continue
                in_body = True
            body_lines.append(line)
    return meta, "".join(body_lines)


def org_body_to_html(body_org: str, tmpfile: Path) -> str:
    """Use emacs --batch to convert an org body to an HTML fragment."""
    tmpfile.write_text(body_org, encoding="utf-8")
    elisp = (
        "(progn "
        " (require 'org) "
        " (require 'ox-html) "
        " (setq org-html-toplevel-hlevel 2) "
        " (setq org-export-with-toc nil) "
        " (setq org-export-with-section-numbers nil) "
        " (setq org-html-htmlize-output-type nil) "
        f' (find-file "{tmpfile}") '
        " (org-html-export-as-html nil nil nil t) "  # body-only
        " (princ (buffer-string)))"
    )
    res = subprocess.run(
        ["emacs", "--batch", "--eval", elisp],
        capture_output=True, text=True, check=True,
    )
    return res.stdout


def render_card(meta: dict, slug: str) -> str:
    title = html.escape(meta.get("TITLE", "(untitled)"))
    original = html.escape(meta.get("ORIGINAL_TITLE", ""))
    authors = html.escape(meta.get("AUTHORS", ""))
    journal = html.escape(meta.get("JOURNAL", ""))
    year = html.escape(meta.get("YEAR", ""))
    date_str = html.escape(meta.get("DATE", ""))
    abstract = html.escape(meta.get("ABSTRACT", ""))
    journal_line = f"{journal}（{year}）" if year else journal

    return f"""      <a class="paper-card" href="p/{slug}.html">
        <div class="pc-date">{date_str}</div>
        <h2 class="pc-title">{title}</h2>
        <div class="pc-original">{original}</div>
        <div class="pc-meta">
          <div><strong>作者</strong>{authors}</div>
          <div><strong>期刊</strong>{journal_line}</div>
        </div>
        <p class="pc-abstract">{abstract}</p>
        <div class="pc-cta">閱讀全文 →</div>
      </a>"""


def render_paper_page(meta: dict, body_html: str, tmpl: str) -> str:
    title = html.escape(meta.get("TITLE", "(untitled)"))
    original = html.escape(meta.get("ORIGINAL_TITLE", ""))
    authors = html.escape(meta.get("AUTHORS", ""))
    year = html.escape(meta.get("YEAR", ""))
    date_str = html.escape(meta.get("DATE", ""))
    abstract = html.escape(meta.get("ABSTRACT", ""))

    journal = html.escape(meta.get("JOURNAL", ""))
    journal_url = meta.get("JOURNAL_URL", "").strip()
    if journal_url:
        journal_html = f'<a href="{html.escape(journal_url)}" target="_blank" rel="noopener">{journal}</a>'
    else:
        journal_html = journal

    extra: list[str] = []
    if meta.get("LINK"):
        extra.append(
            f'<div class="row"><span class="label">論文</span>'
            f'<a href="{html.escape(meta["LINK"])}" target="_blank" rel="noopener">下載/原文連結</a></div>'
        )
    if meta.get("PDF"):
        extra.append(
            f'<div class="row"><span class="label">本機 PDF</span>'
            f'<a href="../{html.escape(meta["PDF"])}" target="_blank">{html.escape(meta["PDF"])}</a></div>'
        )

    return (tmpl
            .replace("{{TITLE}}", title)
            .replace("{{ORIGINAL_TITLE}}", original)
            .replace("{{AUTHORS}}", authors)
            .replace("{{JOURNAL_HTML}}", journal_html)
            .replace("{{YEAR}}", year)
            .replace("{{DATE}}", date_str)
            .replace("{{ABSTRACT}}", abstract)
            .replace("{{EXTRA_LINKS}}", "\n".join(extra))
            .replace("{{BODY}}", body_html))


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    index_tmpl = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    paper_tmpl = (TEMPLATES / "paper.html").read_text(encoding="utf-8")
    tmp = ROOT / ".build_tmp.org"

    entries: list[tuple[str, dict]] = []
    try:
        for org_path in sorted(SRC_DIR.glob("*.org")):
            slug = org_path.stem
            print(f"[build] {slug}", file=sys.stderr)
            meta, body_org = parse_org(org_path)
            if "TITLE" not in meta:
                print(f"  ! missing #+TITLE, skipped", file=sys.stderr)
                continue
            body_html = org_body_to_html(body_org, tmp)
            page = render_paper_page(meta, body_html, paper_tmpl)
            (OUT_DIR / f"{slug}.html").write_text(page, encoding="utf-8")
            entries.append((slug, meta))
    finally:
        if tmp.exists():
            tmp.unlink()

    entries.sort(key=lambda x: x[1].get("DATE", ""), reverse=True)
    cards = "\n".join(render_card(m, s) for s, m in entries)

    index = (index_tmpl
             .replace("{{CARDS}}", cards)
             .replace("{{COUNT}}", str(len(entries)))
             .replace("{{UPDATED}}", date.today().isoformat()))
    (ROOT / "index.html").write_text(index, encoding="utf-8")
    print(f"[build] done: {len(entries)} paper(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
