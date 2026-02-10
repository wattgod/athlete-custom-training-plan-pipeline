#!/usr/bin/env python3
"""
Email delivery for training packages.

Supports:
- SendGrid API
- SMTP (Gmail, etc.)
- Local file output (for testing)
"""

import os
import sys
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from config_loader import get_config
    config = get_config()
except ImportError:
    config = None


class EmailDelivery:
    """Handles email delivery of training packages."""

    DEFAULT_FROM_EMAIL = "coach@gravelgod.com"
    DEFAULT_FROM_NAME = "Gravel God Coaching"

    def __init__(self):
        self.provider = self._get_provider()

    def _get_provider(self) -> str:
        """Determine email provider from config/env."""
        if config:
            provider = config.get('email.provider', 'none')
        else:
            provider = os.environ.get('GG_EMAIL_PROVIDER', 'none')
        return provider.lower()

    def send_package(
        self,
        to_email: str,
        athlete_name: str,
        guide_path: Path,
        workouts_dir: Path,
        guide_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Send training package to athlete.

        Args:
            to_email: Athlete's email address
            athlete_name: Athlete's name for personalization
            guide_path: Path to PDF or HTML guide
            workouts_dir: Directory containing ZWO files
            guide_url: Optional hosted URL for the guide

        Returns:
            (success, message) tuple
        """
        if self.provider == 'none':
            return False, "Email delivery disabled (provider=none). Set GG_EMAIL_PROVIDER or update config.yaml"

        if self.provider == 'sendgrid':
            return self._send_via_sendgrid(to_email, athlete_name, guide_path, workouts_dir, guide_url)
        elif self.provider == 'smtp':
            return self._send_via_smtp(to_email, athlete_name, guide_path, workouts_dir, guide_url)
        elif self.provider == 'file':
            return self._save_to_file(to_email, athlete_name, guide_path, workouts_dir, guide_url)
        else:
            return False, f"Unknown email provider: {self.provider}"

    def _build_email_body(
        self,
        athlete_name: str,
        guide_url: Optional[str] = None,
        has_attachment: bool = True
    ) -> Tuple[str, str]:
        """Build email body (plain text and HTML versions)."""
        first_name = athlete_name.split()[0] if athlete_name else "Athlete"

        plain_text = f"""Hi {first_name},

Your custom training plan is ready!

"""
        if guide_url:
            plain_text += f"""📖 Training Guide: {guide_url}

"""
        if has_attachment:
            plain_text += """📎 Your training guide PDF and workout files are attached.

"""

        plain_text += """The guide includes:
- Your personalized training philosophy
- Week-by-week training structure
- Fueling strategy for race day
- Race-specific preparation tips

The ZWO workout files can be imported into Zwift. Simply copy them to your Zwift workouts folder.

Let me know if you have any questions!

Best,
Coach Matt
Gravel God Coaching

---
This email was sent automatically by the Gravel God Training System.
"""

        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #3a2e25; }}
        .cta {{ background: #B7950B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px 0; }}
        .features {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .features ul {{ margin: 10px 0; padding-left: 20px; }}
        .footer {{ color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Your Training Plan is Ready! 🚴</h1>

        <p>Hi {first_name},</p>

        <p>Your custom training plan has been generated and is ready for you.</p>
"""

        if guide_url:
            html += f"""
        <p><a href="{guide_url}" class="cta">View Your Training Guide →</a></p>
"""

        if has_attachment:
            html += """
        <p>📎 Your training guide PDF and workout files are attached to this email.</p>
"""

        html += """
        <div class="features">
            <strong>Your guide includes:</strong>
            <ul>
                <li>Personalized training philosophy</li>
                <li>Week-by-week training structure</li>
                <li>Fueling strategy for race day</li>
                <li>Race-specific preparation tips</li>
            </ul>
        </div>

        <p><strong>ZWO Workout Files:</strong> Copy the attached .zwo files to your Zwift workouts folder to use them on the trainer.</p>

        <p>Let me know if you have any questions!</p>

        <p>Best,<br>
        <strong>Coach Matt</strong><br>
        Gravel God Coaching</p>

        <div class="footer">
            This email was sent automatically by the Gravel God Training System.
        </div>
    </div>
</body>
</html>
"""

        return plain_text, html

    def _send_via_sendgrid(
        self,
        to_email: str,
        athlete_name: str,
        guide_path: Path,
        workouts_dir: Path,
        guide_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Send via SendGrid API."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
            import base64
        except ImportError:
            return False, "SendGrid not installed. Run: pip install sendgrid"

        api_key = os.environ.get('SENDGRID_API_KEY')
        if config:
            api_key = api_key or config.get('email.sendgrid.api_key')

        if not api_key:
            return False, "SENDGRID_API_KEY not set"

        from_email = os.environ.get('SENDGRID_FROM_EMAIL', self.DEFAULT_FROM_EMAIL)
        if config:
            from_email = config.get('email.sendgrid.from_email', from_email)

        plain_text, html = self._build_email_body(athlete_name, guide_url)

        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=f"Your Custom Training Plan is Ready!",
            plain_text_content=plain_text,
            html_content=html
        )

        # Attach guide PDF
        if guide_path.exists():
            with open(guide_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode()

            attachment = Attachment(
                FileContent(data),
                FileName(guide_path.name),
                FileType('application/pdf'),
                Disposition('attachment')
            )
            message.add_attachment(attachment)

        # Create ZIP of workouts and attach
        if workouts_dir.exists():
            import zipfile
            import tempfile

            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                zip_path = Path(tmp.name)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for zwo_file in workouts_dir.glob('*.zwo'):
                    zf.write(zwo_file, zwo_file.name)

            with open(zip_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode()

            attachment = Attachment(
                FileContent(data),
                FileName('workouts.zip'),
                FileType('application/zip'),
                Disposition('attachment')
            )
            message.add_attachment(attachment)

            zip_path.unlink()  # Clean up temp file

        try:
            sg = sendgrid.SendGridAPIClient(api_key)
            response = sg.send(message)

            if response.status_code in (200, 201, 202):
                return True, f"Email sent via SendGrid (status {response.status_code})"
            else:
                return False, f"SendGrid returned status {response.status_code}"

        except Exception as e:
            return False, f"SendGrid error: {str(e)}"

    def _send_via_smtp(
        self,
        to_email: str,
        athlete_name: str,
        guide_path: Path,
        workouts_dir: Path,
        guide_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Send via SMTP."""
        smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_pass = os.environ.get('SMTP_PASS', '')

        if config:
            smtp_host = config.get('email.smtp.host', smtp_host)
            smtp_port = int(config.get('email.smtp.port', smtp_port))
            smtp_user = config.get('email.smtp.username', smtp_user)
            smtp_pass = config.get('email.smtp.password', smtp_pass)

        if not smtp_user or not smtp_pass:
            return False, "SMTP credentials not configured (SMTP_USER, SMTP_PASS)"

        plain_text, html = self._build_email_body(athlete_name, guide_url)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Your Custom Training Plan is Ready!"
        msg['From'] = f"{self.DEFAULT_FROM_NAME} <{smtp_user}>"
        msg['To'] = to_email

        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        # Attach guide
        if guide_path.exists():
            with open(guide_path, 'rb') as f:
                part = MIMEBase('application', 'pdf')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{guide_path.name}"')
                msg.attach(part)

        # Attach workouts ZIP
        if workouts_dir.exists():
            import zipfile
            import tempfile

            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                zip_path = Path(tmp.name)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for zwo_file in workouts_dir.glob('*.zwo'):
                    zf.write(zwo_file, zwo_file.name)

            with open(zip_path, 'rb') as f:
                part = MIMEBase('application', 'zip')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="workouts.zip"')
                msg.attach(part)

            zip_path.unlink()

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            return True, f"Email sent via SMTP ({smtp_host})"

        except Exception as e:
            return False, f"SMTP error: {str(e)}"

    def _save_to_file(
        self,
        to_email: str,
        athlete_name: str,
        guide_path: Path,
        workouts_dir: Path,
        guide_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Save email to file (for testing)."""
        plain_text, html = self._build_email_body(athlete_name, guide_url)

        output_dir = Path.home() / 'Downloads' / 'email_previews'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        athlete_id = athlete_name.lower().replace(' ', '-')

        # Save plain text
        txt_path = output_dir / f"{timestamp}_{athlete_id}_email.txt"
        with open(txt_path, 'w') as f:
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: Your Custom Training Plan is Ready!\n")
            f.write(f"---\n\n")
            f.write(plain_text)

        # Save HTML
        html_path = output_dir / f"{timestamp}_{athlete_id}_email.html"
        with open(html_path, 'w') as f:
            f.write(html)

        return True, f"Email preview saved to {output_dir}"


def send_training_package(
    athlete_id: str,
    to_email: str = None,
    guide_url: str = None
) -> Tuple[bool, str]:
    """
    Send training package to athlete.

    Args:
        athlete_id: Athlete directory name
        to_email: Email address (defaults to profile email)
        guide_url: Optional hosted guide URL
    """
    import yaml

    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id

    if not athlete_dir.exists():
        return False, f"Athlete not found: {athlete_id}"

    # Load profile
    profile_path = athlete_dir / 'profile.yaml'
    if not profile_path.exists():
        return False, "profile.yaml not found"

    with open(profile_path) as f:
        profile = yaml.safe_load(f)

    athlete_name = profile.get('name', athlete_id)
    if not to_email:
        to_email = profile.get('email')

    if not to_email:
        return False, "No email address provided or found in profile"

    # Find guide and workouts
    guide_path = athlete_dir / 'training_guide.pdf'
    if not guide_path.exists():
        guide_path = athlete_dir / 'training_guide.html'

    workouts_dir = athlete_dir / 'workouts'

    if not guide_path.exists():
        return False, f"Guide not found: {guide_path}"

    # Send
    delivery = EmailDelivery()
    return delivery.send_package(
        to_email=to_email,
        athlete_name=athlete_name,
        guide_path=guide_path,
        workouts_dir=workouts_dir,
        guide_url=guide_url
    )


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 email_delivery.py <athlete_id> [email] [guide_url]")
        print("\nEnvironment variables:")
        print("  GG_EMAIL_PROVIDER: sendgrid, smtp, file, or none")
        print("  SENDGRID_API_KEY: SendGrid API key")
        print("  SMTP_USER, SMTP_PASS: SMTP credentials")
        sys.exit(1)

    athlete_id = sys.argv[1]
    to_email = sys.argv[2] if len(sys.argv) > 2 else None
    guide_url = sys.argv[3] if len(sys.argv) > 3 else None

    success, message = send_training_package(athlete_id, to_email, guide_url)

    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
        sys.exit(1)
