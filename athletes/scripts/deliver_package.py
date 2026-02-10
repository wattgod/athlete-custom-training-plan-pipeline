#!/usr/bin/env python3
"""
Deliver athlete training package:
- Copy guide to delivery folder (for hosting)
- Copy workouts to Downloads
- Run final QC checks
- Output delivery URLs/paths

Usage: python3 deliver_package.py <athlete_id>
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Import integrity tests
from test_athlete_integrity import run_integrity_check, load_yaml_safe


def deliver_package(athlete_id: str) -> dict:
    """Prepare athlete package for delivery."""

    athletes_dir = Path(__file__).parent.parent
    athlete_dir = athletes_dir / athlete_id
    delivery_dir = athletes_dir.parent / 'delivery' / 'guides'
    downloads_dir = Path.home() / 'Downloads' / f'{athlete_id}-package'

    if not athlete_dir.exists():
        print(f"ERROR: Athlete directory not found: {athlete_dir}")
        return {'success': False, 'error': 'Athlete not found'}

    print("=" * 60)
    print(f"DELIVERING PACKAGE: {athlete_id}")
    print("=" * 60)

    # Load profile for athlete name
    profile = load_yaml_safe(athlete_dir / 'profile.yaml')
    athlete_name = profile.get('name', athlete_id) if profile else athlete_id

    # === STEP 1: Run QC ===
    print("\n1. Running quality control checks...")
    qc_passed = run_integrity_check(athlete_id)

    if not qc_passed:
        print("\n❌ QC FAILED - Fix issues before delivery")
        return {'success': False, 'error': 'QC failed'}

    # === STEP 2: Check required files exist ===
    print("\n2. Checking required files...")
    guide_path = athlete_dir / 'training_guide.html'
    workouts_dir = athlete_dir / 'workouts'

    missing = []
    if not guide_path.exists():
        missing.append('training_guide.html')
    if not workouts_dir.exists() or not list(workouts_dir.glob('*.zwo')):
        missing.append('workouts/*.zwo')

    if missing:
        print(f"   ❌ Missing: {missing}")
        print("   Run: python3 generate_athlete_package.py {athlete_id}")
        return {'success': False, 'error': f'Missing files: {missing}'}

    workout_count = len(list(workouts_dir.glob('*.zwo')))
    print(f"   ✓ Guide: {guide_path.name}")
    print(f"   ✓ Workouts: {workout_count} ZWO files")

    # === STEP 3: Copy to delivery folder (for hosting) ===
    print("\n3. Copying to delivery folder...")
    delivery_dir.mkdir(parents=True, exist_ok=True)

    # Use athlete_id as filename for hosted guide
    hosted_guide_path = delivery_dir / f'{athlete_id}.html'
    shutil.copy2(guide_path, hosted_guide_path)
    print(f"   ✓ Copied to: {hosted_guide_path}")

    # === STEP 4: Copy to Downloads for client delivery ===
    print("\n4. Preparing Downloads package...")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    downloads_workouts = downloads_dir / 'workouts'
    downloads_workouts.mkdir(exist_ok=True)

    # Clear and copy guide
    shutil.copy2(guide_path, downloads_dir / 'training_guide.html')

    # Clear and copy workouts
    for old_file in downloads_workouts.glob('*.zwo'):
        old_file.unlink()
    for zwo_file in workouts_dir.glob('*.zwo'):
        shutil.copy2(zwo_file, downloads_workouts / zwo_file.name)

    print(f"   ✓ Guide HTML: ~/Downloads/{athlete_id}-package/training_guide.html")
    print(f"   ✓ Workouts: ~/Downloads/{athlete_id}-package/workouts/ ({workout_count} files)")

    # === STEP 5: Generate PDF ===
    print("\n5. Generating PDF...")
    pdf_path = downloads_dir / 'training_guide.pdf'
    html_path = downloads_dir / 'training_guide.html'

    try:
        from pdf_generator import generate_pdf, get_available_engines
        available = get_available_engines()
        if available:
            print(f"   Available engines: {', '.join(available)}")
        success, message = generate_pdf(html_path, pdf_path)
        if success:
            print(f"   ✓ {message}")
        else:
            print(f"   ⚠ {message}")
    except ImportError:
        # Fallback to direct Chrome if pdf_generator not available
        import subprocess
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        try:
            result = subprocess.run([
                chrome_path, "--headless", "--disable-gpu",
                f"--print-to-pdf={pdf_path}", "--no-margins",
                f"file://{html_path}"
            ], capture_output=True, text=True, timeout=60)
            if pdf_path.exists():
                print(f"   ✓ PDF: {pdf_path.stat().st_size // 1024} KB")
            else:
                print(f"   ⚠ PDF generation failed")
        except Exception as e:
            print(f"   ⚠ PDF generation error: {e}")

    # === STEP 6: Generate delivery info ===
    print("\n" + "=" * 60)
    print("DELIVERY READY")
    print("=" * 60)

    print(f"\n📋 Athlete: {athlete_name}")
    print(f"📁 Downloads: ~/Downloads/{athlete_id}-package/")

    print("\n📎 FILES TO SEND:")
    print(f"   • Training Guide (PDF): ~/Downloads/{athlete_id}-package/training_guide.pdf")
    print(f"   • Workouts Folder: ~/Downloads/{athlete_id}-package/workouts/")

    print("\n🌐 FOR HOSTED URL:")
    print(f"   1. Push delivery/guides/{athlete_id}.html to your hosting repo")
    print(f"   2. URL will be: https://YOUR-DOMAIN/guides/{athlete_id}.html")
    print(f"   ")
    print(f"   Or use GitHub Pages:")
    print(f"   cd /Users/mattirowe/Documents/GravelGod/athlete-profiles/delivery")
    print(f"   git add . && git commit -m 'Add {athlete_name} guide' && git push")

    # === STEP 7: Email delivery (if enabled) ===
    athlete_email = profile.get('email', '') if profile else ''
    email_sent = False

    if athlete_email:
        print(f"\n✉️  EMAIL DELIVERY:")
        print(f"   Athlete email: {athlete_email}")

        try:
            from email_delivery import EmailDelivery
            delivery = EmailDelivery()

            if delivery.provider != 'none':
                print(f"   Provider: {delivery.provider}")
                user_input = input("   Send email now? [y/N]: ").strip().lower()

                if user_input == 'y':
                    guide_url = f"https://wattgod.github.io/gravel-god-guides/athletes/{athlete_id}/"
                    success, msg = delivery.send_package(
                        to_email=athlete_email,
                        athlete_name=athlete_name,
                        guide_path=pdf_path if pdf_path.exists() else (downloads_dir / 'training_guide.html'),
                        workouts_dir=downloads_workouts,
                        guide_url=guide_url
                    )
                    if success:
                        print(f"   ✓ {msg}")
                        email_sent = True
                    else:
                        print(f"   ✗ {msg}")
            else:
                print("   Email delivery disabled (GG_EMAIL_PROVIDER=none)")
                print("   To enable: export GG_EMAIL_PROVIDER=sendgrid (or smtp)")
        except ImportError:
            print("   Email module not available")
    else:
        print("\n⚠️  No email address in profile - skipping email delivery")

    print("\n✉️  MANUAL EMAIL TEMPLATE:")
    print("-" * 40)
    print(f"""
Hi {athlete_name.split()[0]},

Your custom training plan is ready!

📖 Training Guide: [PASTE URL HERE]
📂 Workouts: [Attached or linked]

The guide includes:
- Your personalized training philosophy
- Week-by-week training structure
- Fueling strategy for race day
- Race-specific preparation tips

Workouts can be imported into Zwift or TrainingPeaks.

Let me know if you have any questions!
""")
    print("-" * 40)

    return {
        'success': True,
        'athlete_id': athlete_id,
        'athlete_name': athlete_name,
        'downloads_path': str(downloads_dir),
        'hosted_guide_path': str(hosted_guide_path),
        'workout_count': workout_count,
        'email_sent': email_sent,
        'delivered_at': datetime.now().isoformat()
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 deliver_package.py <athlete_id> [--send-email]")
        sys.exit(1)

    result = deliver_package(sys.argv[1])
    sys.exit(0 if result.get('success') else 1)
