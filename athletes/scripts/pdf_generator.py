#!/usr/bin/env python3
"""
Cross-platform PDF generator for training guides.

Tries multiple PDF engines in order of preference:
1. Chrome/Chromium headless (best quality)
2. WeasyPrint (pure Python, good fallback)
3. wkhtmltopdf (widely available)
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from config_loader import get_config
    config = get_config()
except ImportError:
    config = None


def find_chrome() -> Optional[str]:
    """Find Chrome/Chromium executable."""
    if config:
        path = config.get_chrome_path()
        if path:
            return path

    # Platform-specific defaults
    if sys.platform == 'darwin':
        paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
        ]
    elif sys.platform == 'win32':
        paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        ]
    else:  # Linux
        paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/snap/bin/chromium',
        ]

    for path in paths:
        if Path(path).exists():
            return path

    return None


def find_wkhtmltopdf() -> Optional[str]:
    """Find wkhtmltopdf executable."""
    if sys.platform == 'darwin':
        paths = [
            '/usr/local/bin/wkhtmltopdf',
            '/opt/homebrew/bin/wkhtmltopdf',
        ]
    elif sys.platform == 'win32':
        paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
        ]
    else:
        paths = [
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
        ]

    for path in paths:
        if Path(path).exists():
            return path

    # Try which/where
    try:
        result = subprocess.run(
            ['which', 'wkhtmltopdf'] if sys.platform != 'win32' else ['where', 'wkhtmltopdf'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except Exception:
        pass

    return None


def has_weasyprint() -> bool:
    """Check if WeasyPrint is available."""
    try:
        import weasyprint
        return True
    except ImportError:
        return False
    except OSError as e:
        # Missing C library (pango, cairo, etc.)
        import sys
        print(f"WeasyPrint import failed (system dep missing): {e}", file=sys.stderr)
        return False
    except Exception as e:
        import sys
        print(f"WeasyPrint import failed: {e}", file=sys.stderr)
        return False


# A real training guide is 30+ pages; a handful of pages means the render
# died partway (or printed a stub) and must not be delivered to a customer.
MIN_GUIDE_PAGES = 10


def count_pdf_pages(pdf_path: Path) -> int:
    """Count page objects in a PDF without external deps.

    Counts /Type /Page object markers — NOT the page-tree /Count entry,
    which also appears in outline dictionaries and misled both `file`
    and a debugging session into believing a 40-page PDF had 8 pages.
    """
    import re
    data = pdf_path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


def validate_pdf(pdf_path: Path, min_pages: int = MIN_GUIDE_PAGES) -> Tuple[bool, str]:
    """Sanity-check a generated PDF: header magic + plausible page count."""
    data = pdf_path.read_bytes()
    if not data.startswith(b"%PDF-"):
        return False, "not a PDF (bad magic bytes)"
    if b"%%EOF" not in data[-2048:]:
        return False, "missing %%EOF trailer (truncated write)"
    pages = count_pdf_pages(pdf_path)
    if pages < min_pages:
        return False, f"only {pages} pages (expected >= {min_pages})"
    return True, f"{pages} pages"


def generate_pdf_chrome(html_path: Path, pdf_path: Path, timeout: int = 60) -> Tuple[bool, str]:
    """Generate PDF using Chrome headless."""
    chrome = find_chrome()
    if not chrome:
        return False, "Chrome not found"

    html_url = f"file://{html_path.absolute()}"

    try:
        # Use print-to-pdf with proper settings
        # Note: Do NOT use --no-margins as it overrides CSS @page margins
        # The CSS @media print rules will control margins, page breaks, etc.
        result = subprocess.run([
            chrome,
            "--headless=new",  # Use new headless mode (better rendering)
            "--disable-gpu",
            "--no-sandbox",  # Required for Docker/CI
            "--disable-dev-shm-usage",  # Containers have tiny /dev/shm; use /tmp instead
            "--disable-software-rasterizer",
            "--run-all-compositor-stages-before-draw",  # Better rendering
            "--virtual-time-budget=10000",  # Let fonts/layout settle before print
            f"--print-to-pdf={pdf_path}",
            # Modern flag — the old --print-to-pdf-no-header is silently
            # ignored by current Chrome, which shipped PDFs with timestamp
            # headers and file:// footers on every page
            "--no-pdf-header-footer",
            # Let CSS control margins via @page rules
            html_url
        ], capture_output=True, text=True, timeout=timeout)

        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            ok, msg = validate_pdf(pdf_path)
            if not ok:
                return False, f"Chrome produced invalid PDF: {msg}"
            return True, f"Generated with Chrome ({pdf_path.stat().st_size // 1024} KB, {msg})"
        else:
            return False, f"Chrome failed: {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "Chrome timed out"
    except Exception as e:
        return False, f"Chrome error: {e}"


# Rendering runs in a SUBPROCESS so it can be killed on timeout. WeasyPrint
# renders in-process with no cancellation hook; on Railway's shared vCPU the
# full training guide took 30+ minutes of CPU (Jun 2026), hanging every order
# past the webhook's pipeline timeout. Never call weasyprint.write_pdf()
# directly from a server code path.
_WEASYPRINT_RENDER_SNIPPET = (
    "import sys\n"
    "from weasyprint import HTML\n"
    "from weasyprint.text.fonts import FontConfiguration\n"
    "HTML(filename=sys.argv[1]).write_pdf(sys.argv[2], font_config=FontConfiguration())\n"
)


def generate_pdf_weasyprint(html_path: Path, pdf_path: Path, timeout: int = 120) -> Tuple[bool, str]:
    """Generate PDF using WeasyPrint in a time-boxed subprocess."""
    if not has_weasyprint():
        # Try importing directly to get the real error message
        try:
            import weasyprint
        except Exception as e:
            return False, f"WeasyPrint not available: {e}"
        return False, "WeasyPrint not installed"

    try:
        result = subprocess.run(
            [sys.executable, "-c", _WEASYPRINT_RENDER_SNIPPET,
             str(html_path), str(pdf_path)],
            capture_output=True, text=True, timeout=timeout,
        )

        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            ok, msg = validate_pdf(pdf_path)
            if not ok:
                return False, f"WeasyPrint produced invalid PDF: {msg}"
            return True, f"Generated with WeasyPrint ({pdf_path.stat().st_size // 1024} KB, {msg})"
        elif result.returncode != 0:
            tail = (result.stderr or result.stdout or '').strip().splitlines()
            return False, f"WeasyPrint error: {tail[-1] if tail else 'unknown'}"
        else:
            return False, "WeasyPrint produced empty file"

    except subprocess.TimeoutExpired:
        # Partial output from the killed render is garbage — remove it
        pdf_path.unlink(missing_ok=True)
        return False, f"WeasyPrint timed out after {timeout}s"
    except Exception as e:
        return False, f"WeasyPrint error: {e}"


def generate_pdf_wkhtmltopdf(html_path: Path, pdf_path: Path, timeout: int = 60) -> Tuple[bool, str]:
    """Generate PDF using wkhtmltopdf."""
    wkhtmltopdf = find_wkhtmltopdf()
    if not wkhtmltopdf:
        return False, "wkhtmltopdf not found"

    try:
        result = subprocess.run([
            wkhtmltopdf,
            "--quiet",
            "--enable-local-file-access",
            "--margin-top", "10mm",
            "--margin-bottom", "10mm",
            "--margin-left", "10mm",
            "--margin-right", "10mm",
            str(html_path),
            str(pdf_path)
        ], capture_output=True, text=True, timeout=timeout)

        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            ok, msg = validate_pdf(pdf_path)
            if not ok:
                return False, f"wkhtmltopdf produced invalid PDF: {msg}"
            return True, f"Generated with wkhtmltopdf ({pdf_path.stat().st_size // 1024} KB, {msg})"
        else:
            return False, f"wkhtmltopdf failed: {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "wkhtmltopdf timed out"
    except Exception as e:
        return False, f"wkhtmltopdf error: {e}"


def generate_pdf(html_path: Path, pdf_path: Path, timeout: int = 120) -> Tuple[bool, str]:
    """
    Generate PDF from HTML using the best available engine.

    The timeout applies PER ENGINE and must stay well under the webhook's
    PIPELINE_TIMEOUT (480s) — three engines × 120s = 360s worst case.

    Returns (success, message) tuple.
    """
    html_path = Path(html_path)
    pdf_path = Path(pdf_path)

    if not html_path.exists():
        return False, f"HTML file not found: {html_path}"

    # Try engines in order of preference
    engines = [
        ("Chrome", generate_pdf_chrome),
        ("WeasyPrint", generate_pdf_weasyprint),
        ("wkhtmltopdf", generate_pdf_wkhtmltopdf),
    ]

    errors = []
    for name, generator in engines:
        success, message = generator(html_path, pdf_path, timeout)

        if success:
            return True, message
        else:
            errors.append(f"{name}: {message}")

    return False, "All PDF engines failed:\n  " + "\n  ".join(errors)


def get_available_engines() -> list:
    """Return list of available PDF engines."""
    available = []

    if find_chrome():
        available.append("chrome")

    if has_weasyprint():
        available.append("weasyprint")

    if find_wkhtmltopdf():
        available.append("wkhtmltopdf")

    return available


if __name__ == '__main__':
    print("Available PDF engines:", get_available_engines())

    if len(sys.argv) >= 3:
        html_file = Path(sys.argv[1])
        pdf_file = Path(sys.argv[2])

        success, message = generate_pdf(html_file, pdf_file)
        print(f"{'✓' if success else '✗'} {message}")
        sys.exit(0 if success else 1)
    else:
        print("\nUsage: python3 pdf_generator.py <input.html> <output.pdf>")
