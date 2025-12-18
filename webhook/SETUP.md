# Webhook Setup Guide

This guide connects the athlete questionnaire form to GitHub Actions for automated processing.

## Architecture

```
[Questionnaire Form] → [Cloudflare Worker] → [GitHub Actions] → [Email Notification]
     (GitHub Pages)        (validates)         (generates plan)      (sends results)
```

## Step 1: Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: `athlete-intake-worker`
4. Expiration: 90 days (or longer)
5. Scopes: Check `repo` (full control of private repos)
6. Click "Generate token"
7. **COPY THE TOKEN** — you won't see it again

## Step 2: Deploy Cloudflare Worker

### Option A: Cloudflare Dashboard (Easiest)

1. Go to https://dash.cloudflare.com
2. Click "Workers & Pages" in sidebar
3. Click "Create Application" → "Create Worker"
4. Name it: `athlete-intake`
5. Click "Deploy"
6. Click "Edit Code"
7. Delete the default code, paste contents of `worker.js`
8. Click "Save and Deploy"

### Option B: Wrangler CLI

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create wrangler.toml
cat > wrangler.toml << EOF
name = "athlete-intake"
main = "worker.js"
compatibility_date = "2024-01-01"

[vars]
ALLOWED_ORIGINS = "https://wattgod.github.io"
EOF

# Deploy
wrangler deploy
```

## Step 3: Configure Worker Environment Variables

In Cloudflare Dashboard:

1. Go to Workers & Pages → `athlete-intake`
2. Click "Settings" → "Variables"
3. Add these variables:

| Variable | Type | Value |
|----------|------|-------|
| `GITHUB_TOKEN` | Secret | Your GitHub PAT from Step 1 |
| `ALLOWED_ORIGINS` | Text | `https://wattgod.github.io` |

4. Click "Save and Deploy"

## Step 4: Update Form with Worker URL

1. Copy your worker URL (e.g., `https://athlete-intake.gravelgod.workers.dev`)
2. Edit `docs/athlete-questionnaire.html`
3. Find this line near the bottom:
   ```javascript
   const WEBHOOK_URL = 'https://athlete-intake.gravelgod.workers.dev';
   ```
4. Update with your actual worker URL

## Step 5: Configure GitHub Secrets

For the email notifications to work:

1. Go to https://github.com/wattgod/athlete-profiles/settings/secrets/actions
2. Add these secrets:

| Secret | Description |
|--------|-------------|
| `EMAIL_USERNAME` | Gmail address (e.g., `coach@gravelgodcycling.com`) |
| `EMAIL_PASSWORD` | Gmail App Password (not your regular password) |
| `ADMIN_EMAIL` | Your personal email for failure alerts |

### Creating a Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Other (Custom name)"
3. Name it: `Gravel God GitHub Actions`
4. Copy the 16-character password
5. Use this as `EMAIL_PASSWORD`

## Step 6: Test the Integration

### Test 1: Worker Health Check

```bash
curl -X POST https://athlete-intake.gravelgod.workers.dev \
  -H "Content-Type: application/json" \
  -H "Origin: https://wattgod.github.io" \
  -d '{"name":"Test User","email":"test@example.com","coaching_tier":"mid"}'
```

Expected response:
```json
{"success":true,"message":"Intake received! Check your email within 24 hours.","athlete_id":"test-user-xxxx"}
```

### Test 2: Full Form Submission

1. Go to https://wattgod.github.io/athlete-profiles/athlete-questionnaire.html
2. Fill out the form with test data
3. Submit
4. Check GitHub Actions: https://github.com/wattgod/athlete-profiles/actions
5. Verify the workflow runs

### Test 3: Manual Workflow Trigger

1. Go to https://github.com/wattgod/athlete-profiles/actions
2. Click "Athlete Intake" workflow
3. Click "Run workflow"
4. Enter test email and athlete_id
5. Verify email is received

## Troubleshooting

### "Failed to process submission"
- Check GitHub token has `repo` scope
- Verify token isn't expired
- Check worker logs in Cloudflare dashboard

### "Forbidden" error
- Check `ALLOWED_ORIGINS` includes your domain
- Make sure origin header is being sent

### Email not received
- Check GitHub Actions logs for email step
- Verify Gmail App Password is correct
- Check spam folder
- Ensure 2FA is enabled on Gmail (required for App Passwords)

### Workflow not triggering
- Check GitHub Actions is enabled for the repo
- Verify `repository_dispatch` event is configured
- Check worker logs for API call status

## Production Checklist

- [ ] Cloudflare Worker deployed
- [ ] `GITHUB_TOKEN` secret set in worker
- [ ] `ALLOWED_ORIGINS` configured
- [ ] Form `WEBHOOK_URL` updated
- [ ] GitHub secrets configured (EMAIL_USERNAME, EMAIL_PASSWORD, ADMIN_EMAIL)
- [ ] Test submission successful
- [ ] Email received
- [ ] Profile created in repo

## Monitoring

- **Worker analytics**: Cloudflare Dashboard → Workers → athlete-intake → Metrics
- **GitHub Actions**: https://github.com/wattgod/athlete-profiles/actions
- **Errors**: Check worker logs and GitHub Actions logs

## Security Notes

1. **GitHub token**: Only grant `repo` scope, rotate every 90 days
2. **CORS**: Only allow your specific origins
3. **Rate limiting**: Worker includes basic validation; add Cloudflare rate limiting for production
4. **Email validation**: Disposable emails are blocked
5. **Honeypot**: Bots are caught and rejected

