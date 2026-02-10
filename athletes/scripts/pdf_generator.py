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


def generate_pdf_chrome(html_path: Path, pdf_path: Path, timeout: int = 60) -> Tuple[bool, str]:
    """Generate PDF using Chrome headless."""
    chrome = find_chrome()
    if not chrome:
        return False, "Chrome not found"

    html_url = f"file://{html_path.absolute()}"

    try:
        result = subprocess.run([
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",  # Required for Docker/CI
            "--disable-software-rasterizer",
            f"--print-to-pdf={pdf_path}",
            "--no-margins",
            html_url
        ], capture_output=True, text=True, timeout=timeout)

        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return True, f"Generated with Chrome ({pdf_path.stat().st_size // 1024} KB)"
        else:
            return False, f"Chrome failed: {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "Chrome timed out"
    except Exception as e:
        return False, f"Chrome error: {e}"


def generate_pdf_weasyprint(html_path: Path, pdf_path: Path) -> Tuple[bool, str]:
    """Generate PDF using WeasyPrint."""
    if not has_weasyprint():
        return False, "WeasyPrint not installed"

    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()

        # Read HTML
        html = HTML(filename=str(html_path))

        # Generate PDF
        html.write_pdf(
            str(pdf_path),
            font_config=font_config,
        )

        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return True, f"Generated with WeasyPrint ({pdf_path.stat().st_size // 1024} KB)"
        else:
            return False, "WeasyPrint produced empty file"

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
            return True, f"Generated with wkhtmltopdf ({pdf_path.stat().st_size // 1024} KB)"
        else:
            return False, f"wkhtmltopdf failed: {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "wkhtmltopdf timed out"
    except Exception as e:
        return False, f"wkhtmltopdf error: {e}"


def generate_pdf(html_path: Path, pdf_path: Path, timeout: int = 60) -> Tuple[bool, str]:
    """
    Generate PDF from HTML using the best available engine.

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
        if name == "WeasyPrint":
            success, message = generator(html_path, pdf_path)
        else:
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
