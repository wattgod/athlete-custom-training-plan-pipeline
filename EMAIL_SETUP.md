# Email Notification Setup

## Overview

When someone fills out the athlete questionnaire, you'll receive an email notification at **gravelgodcoaching@gmail.com** with their intake details.

## Required GitHub Secrets

You need to configure these secrets in your GitHub repository:

1. Go to: `https://github.com/wattgod/athlete-profiles/settings/secrets/actions`
2. Click "New repository secret"
3. Add these secrets:

### `EMAIL_USERNAME`
- Your Gmail address (e.g., `gravelgodcoaching@gmail.com`)
- Used for sending emails via SMTP

### `EMAIL_PASSWORD`
- **NOT your regular Gmail password**
- You need to create an **App Password**:
  1. Go to https://myaccount.google.com/apppasswords
  2. Select "Mail" and "Other (Custom name)" → "Gravel God System"
  3. Generate password
  4. Copy the 16-character password (no spaces)
  5. Paste as `EMAIL_PASSWORD` secret

### `ADMIN_EMAIL` (Optional)
- Currently set to `gravelgodcoaching@gmail.com` in the workflow
- You can override with this secret if needed

## What Emails Are Sent

### 1. Admin Notification (gravelgodcoaching@gmail.com)
**Sent when:** Plan generation succeeds
**Subject:** 🎯 New Athlete Intake: [Name]
**Contains:**
- Athlete name, email, ID
- Coaching tier selected
- Links to profile and workflow

### 2. Athlete Welcome Email
**Sent to:** The athlete's email
**Subject:** Welcome to Gravel God Coaching - [Name]
**Contains:**
- Confirmation of intake received
- Next steps
- Tier information

### 3. Failure Notifications
**Sent when:** Plan generation fails
- Athlete gets error notification
- Admin gets alert email (if `ADMIN_EMAIL` secret is set)

## Testing

To test email notifications:

1. **Manual trigger:**
   - Go to: `https://github.com/wattgod/athlete-profiles/actions/workflows/athlete-intake.yml`
   - Click "Run workflow"
   - Fill in test data
   - Check your email

2. **Real submission:**
   - Submit the form at: `https://wattgod.github.io/athlete-profiles/athlete-questionnaire.html`
   - Check `gravelgodcoaching@gmail.com` for notification

## Troubleshooting

**No emails received?**
- Check GitHub Actions workflow logs for email errors
- Verify secrets are set correctly
- Check spam folder
- Ensure `EMAIL_USERNAME` and `EMAIL_PASSWORD` are valid

**"Authentication failed" errors?**
- Make sure you're using an App Password, not your regular Gmail password
- Verify the App Password is correct (16 characters, no spaces)

**Emails going to spam?**
- Gmail may flag automated emails
- Check spam folder
- Consider setting up SPF/DKIM records (advanced)

## Current Configuration

- **Admin Email:** `gravelgodcoaching@gmail.com` (hardcoded in workflow)
- **SMTP Server:** `smtp.gmail.com`
- **Port:** `465` (SSL)
- **From Address:** Uses `EMAIL_USERNAME` secret

