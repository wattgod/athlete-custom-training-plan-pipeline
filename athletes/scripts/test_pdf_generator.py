#!/usr/bin/env python3
"""
Tests for pdf_generator.py — focused on the production failure mode found
June 2026: WeasyPrint rendering in-process with no timeout burned 30+ minutes
of CPU on Railway and timed out every real order. The render now runs in a
killable subprocess.

Run with: python3 -m pytest test_pdf_generator.py -v
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import pdf_generator


@pytest.fixture
def html_file(tmp_path):
    p = tmp_path / 'guide.html'
    p.write_text('<html><body><h1>Guide</h1></body></html>')
    return p


class TestWeasyprintTimebox:
    """The WeasyPrint fallback must be killable — never hang an order."""

    def test_timeout_kills_subprocess_and_reports(self, html_file, tmp_path):
        pdf = tmp_path / 'out.pdf'
        slow = "import time; time.sleep(30)"
        with patch.object(pdf_generator, 'has_weasyprint', return_value=True), \
             patch.object(pdf_generator, '_WEASYPRINT_RENDER_SNIPPET', slow):
            ok, msg = pdf_generator.generate_pdf_weasyprint(html_file, pdf, timeout=1)
        assert ok is False
        assert 'timed out' in msg

    def test_timeout_removes_partial_pdf(self, html_file, tmp_path):
        pdf = tmp_path / 'out.pdf'
        slow = (
            "import sys, time\n"
            "open(sys.argv[2], 'w').write('partial')\n"
            "time.sleep(30)\n"
        )
        with patch.object(pdf_generator, 'has_weasyprint', return_value=True), \
             patch.object(pdf_generator, '_WEASYPRINT_RENDER_SNIPPET', slow):
            ok, _ = pdf_generator.generate_pdf_weasyprint(html_file, pdf, timeout=1)
        assert ok is False
        assert not pdf.exists()

    def test_success_when_subprocess_writes_pdf(self, html_file, tmp_path):
        pdf = tmp_path / 'out.pdf'
        # A realistic PDF: valid magic, page objects, and an EOF trailer.
        # generate_pdf_weasyprint now validates output (a real render is
        # multi-page) so the fixture must look like a real document.
        fake = (
            "import sys\n"
            "pages = b''.join(b'%d 0 obj << /Type /Page >> endobj\\n' % (i+10) "
            "for i in range(12))\n"
            "open(sys.argv[2], 'wb').write(b'%PDF-1.4\\n' + pages + b'%%EOF\\n')\n"
        )
        with patch.object(pdf_generator, 'has_weasyprint', return_value=True), \
             patch.object(pdf_generator, '_WEASYPRINT_RENDER_SNIPPET', fake):
            ok, msg = pdf_generator.generate_pdf_weasyprint(html_file, pdf, timeout=10)
        assert ok is True
        assert 'WeasyPrint' in msg

    def test_subprocess_error_surfaces_message(self, html_file, tmp_path):
        pdf = tmp_path / 'out.pdf'
        boom = "raise RuntimeError('render exploded')"
        with patch.object(pdf_generator, 'has_weasyprint', return_value=True), \
             patch.object(pdf_generator, '_WEASYPRINT_RENDER_SNIPPET', boom):
            ok, msg = pdf_generator.generate_pdf_weasyprint(html_file, pdf, timeout=10)
        assert ok is False
        assert 'render exploded' in msg


class TestEngineOrder:
    """Chrome stays the preferred engine; every engine gets the timeout."""

    def test_chrome_tried_first(self, html_file, tmp_path):
        calls = []

        def fake_engine(name, ok):
            def run(h, p, timeout):
                calls.append((name, timeout))
                return ok, name
            return run

        with patch.object(pdf_generator, 'generate_pdf_chrome', fake_engine('chrome', True)), \
             patch.object(pdf_generator, 'generate_pdf_weasyprint', fake_engine('weasy', True)), \
             patch.object(pdf_generator, 'generate_pdf_wkhtmltopdf', fake_engine('wk', True)):
            ok, msg = pdf_generator.generate_pdf(html_file, tmp_path / 'o.pdf', timeout=99)

        assert ok is True
        assert calls == [('chrome', 99)]

    def test_falls_back_with_timeout_propagated(self, html_file, tmp_path):
        calls = []

        def fake_engine(name, ok):
            def run(h, p, timeout):
                calls.append((name, timeout))
                return ok, name
            return run

        with patch.object(pdf_generator, 'generate_pdf_chrome', fake_engine('chrome', False)), \
             patch.object(pdf_generator, 'generate_pdf_weasyprint', fake_engine('weasy', True)), \
             patch.object(pdf_generator, 'generate_pdf_wkhtmltopdf', fake_engine('wk', True)):
            ok, _ = pdf_generator.generate_pdf(html_file, tmp_path / 'o.pdf', timeout=42)

        assert ok is True
        assert calls == [('chrome', 42), ('weasy', 42)]

    def test_chromium_path_known_for_railway_image(self):
        """The Docker image installs Debian's `chromium` — find_chrome must look there."""
        # Guard against someone trimming the Linux path list
        import inspect
        src = inspect.getsource(pdf_generator.find_chrome)
        assert "'/usr/bin/chromium'" in src


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
