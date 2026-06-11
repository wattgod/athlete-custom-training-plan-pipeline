"""PDF generation quality guards.

Jesse Couch (Jun 2026) received a guide PDF with browser headers, a
one-word-per-line title, the TOC printed over body text, and vertically
wrapped table headers. Root causes: no @media print CSS in the shipped
guide (a comment promised a print.css injection step that never existed),
a deprecated Chrome flag, and zero output validation.
"""

from pathlib import Path

import pytest

from pdf_generator import count_pdf_pages, validate_pdf, MIN_GUIDE_PAGES
from training_guide_builder import _css, _meta_badges


def _mini_pdf(n_pages: int) -> bytes:
    pages = b"".join(
        b"%d 0 obj << /Type /Page /Parent 1 0 R >> endobj\n" % (i + 10)
        for i in range(n_pages)
    )
    return b"%PDF-1.4\n" + pages + b"\n%%EOF\n"


class TestValidatePdf:
    def test_counts_page_objects_not_outline_count(self, tmp_path):
        # /Count appears in outlines too — Jesse's 35-page PDF read as "8"
        p = tmp_path / "t.pdf"
        p.write_bytes(
            b"%PDF-1.4\n2 0 obj << /Type /Outlines /Count 8 >> endobj\n"
            + _mini_pdf(40)[9:]
        )
        assert count_pdf_pages(p) == 40

    def test_rejects_short_pdf(self, tmp_path):
        p = tmp_path / "short.pdf"
        p.write_bytes(_mini_pdf(3))
        ok, msg = validate_pdf(p)
        assert not ok
        assert "3 pages" in msg

    def test_rejects_bad_magic(self, tmp_path):
        p = tmp_path / "junk.pdf"
        p.write_bytes(b"<html>not a pdf</html>")
        ok, msg = validate_pdf(p)
        assert not ok
        assert "magic" in msg

    def test_rejects_truncated_write(self, tmp_path):
        p = tmp_path / "trunc.pdf"
        p.write_bytes(_mini_pdf(MIN_GUIDE_PAGES + 5).replace(b"%%EOF", b""))
        ok, msg = validate_pdf(p)
        assert not ok
        assert "EOF" in msg

    def test_accepts_plausible_guide(self, tmp_path):
        p = tmp_path / "ok.pdf"
        p.write_bytes(_mini_pdf(MIN_GUIDE_PAGES + 20))
        ok, msg = validate_pdf(p)
        assert ok
        assert f"{MIN_GUIDE_PAGES + 20} pages" in msg

    def test_pages_word_not_counted(self, tmp_path):
        # /Type /Pages (the tree node) must not count as a page
        p = tmp_path / "tree.pdf"
        p.write_bytes(
            b"%PDF-1.4\n1 0 obj << /Type /Pages /Count 2 >> endobj\n"
            + _mini_pdf(2)[9:]
        )
        assert count_pdf_pages(p) == 2


class TestGuidePrintCss:
    """The shipped guide HTML must carry its own print stylesheet."""

    def test_print_block_present(self):
        css = _css()
        assert "@media print" in css

    def test_layout_flattened_for_print(self):
        # Chromium can't fragment the 260px grid — content gets squeezed
        css = _css()
        print_block = css[css.find("@media print"):]
        assert ".gg-guide-layout { display: block; }" in print_block
        assert "nav.gg-guide-toc { display: none; }" in print_block

    def test_components_avoid_page_breaks(self):
        css = _css()
        print_block = css[css.find("@media print"):]
        assert "break-inside: avoid" in print_block
        assert "@page" in print_block


class TestMetaBadges:
    def test_drops_empty_and_placeholder_values(self):
        html = _meta_badges("Borderlands", 100, None, "", 21, "TBD")
        assert "Borderlands" in html
        assert "100 miles" in html
        assert "ft" not in html        # no orphan unit badge
        assert "TBD" not in html       # no placeholder badge
        assert "21-week plan" in html
        assert "<span></span>" not in html

    def test_keeps_real_values(self):
        html = _meta_badges("Unbound", 200, 11000, "", 16, "Emporia, KS")
        assert "11000 ft" in html
        assert "Emporia, KS" in html
