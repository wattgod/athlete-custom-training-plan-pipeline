# WooCommerce + Stripe Setup Guide

## 1. Create WooCommerce Products

Create 3 **Virtual** products in WooCommerce:

| Product Name | SKU | Price | Description |
|--------------|-----|-------|-------------|
| Custom Training Plan - Starter | training-starter | $99 | Up to 8 weeks. Perfect for short builds or race-specific prep. |
| Custom Training Plan - Race Ready | training-race-ready | $149 | Up to 16 weeks. Full periodized training block. |
| Custom Training Plan - Full Build | training-full-build | $199 | Unlimited weeks. Complete season preparation. |

### Product Settings:
- **Type:** Simple product
- **Virtual:** ✓ Yes
- **Downloadable:** ✗ No (delivery via email)
- **Sold Individually:** ✓ Yes

---

## 2. Install Required Plugins

1. **WooCommerce** (if not already installed)
2. **WooCommerce Stripe Gateway** (official plugin)
3. **WooCommerce Checkout Field Editor** OR **Flexible Checkout Fields**

---

## 3. Configure Stripe

1. Go to **WooCommerce → Settings → Payments → Stripe**
2. Enable Stripe
3. Add your API keys:
   - Live Publishable Key: `pk_live_...`
   - Live Secret Key: `sk_live_...`
4. Enable **Stripe Checkout** (hosted checkout page - more secure)

---

## 4. Add Custom Checkout Fields

Using **Flexible Checkout Fields** or similar, add these fields to checkout:

### Required Fields (add to Order section):

| Field Name | Type | Label | Required |
|------------|------|-------|----------|
| `age` | Number | Age | Yes |
| `weight_kg` | Number | Weight (kg) | Yes |
| `ftp_watts` | Number | Current FTP (watts) | Yes |
| `race_name` | Text | Target Race Name | Yes |
| `race_date` | Date | Race Date | Yes |
| `race_distance_miles` | Number | Race Distance (miles) | Yes |
| `race_elevation_ft` | Number | Elevation Gain (ft) | No |
| `race_terrain` | Select | Terrain Type | No |
| `cycling_hours` | Number | Weekly Training Hours Available | Yes |
| `strength_hours` | Number | Weekly Strength Training Hours | No |
| `preferred_long_day` | Select | Preferred Long Ride Day | No |
| `experience_level` | Select | Experience Level | Yes |
| `race_goal` | Select | Race Goal | Yes |
| `limiters` | Textarea | Known Limiters/Weaknesses | No |
| `notes` | Textarea | Additional Notes | No |

### Select Field Options:

**race_terrain:**
- gravel
- mixed
- road
- mtb

**preferred_long_day:**
- saturday
- sunday

**experience_level:**
- beginner
- intermediate
- advanced

**race_goal:**
- finish (Finish Strong)
- compete (Compete in Age Group)
- podium (Podium/Win)

---

## 5. Configure Webhook

1. Go to **WooCommerce → Settings → Advanced → Webhooks**
2. Click **Add Webhook**
3. Configure:
   - **Name:** Training Plan Generator
   - **Status:** Active
   - **Topic:** Order updated
   - **Delivery URL:** `https://your-webhook-url.railway.app/webhook/woocommerce`
   - **Secret:** Generate a strong secret (save this for server config)
4. Save

---

## 6. Deploy Webhook Server

### Option A: Railway (Recommended)

1. Create account at [railway.app](https://railway.app)
2. Connect GitHub repo
3. Add environment variables:
   ```
   WOOCOMMERCE_SECRET=your-webhook-secret
   ATHLETES_DIR=/app/athletes
   SCRIPTS_DIR=/app/athletes/scripts
   ```
4. Deploy

### Option B: Render

1. Create account at [render.com](https://render.com)
2. Create new **Web Service**
3. Connect GitHub repo
4. Configure:
   - **Build Command:** `pip install -r webhook/requirements.txt`
   - **Start Command:** `gunicorn --chdir webhook app:app`
5. Add environment variables
6. Deploy

---

## 7. Test the Flow

### Manual Test:
1. Place a test order using Stripe test mode
2. Check webhook logs in WooCommerce
3. Verify athlete profile created
4. Confirm email delivery

### Webhook Test Endpoint:
```bash
curl -X POST https://your-webhook-url/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": "test_athlete",
    "tier": "race_ready",
    "profile": {
      "name": "Test Athlete",
      "email": "you@example.com",
      "target_race": {
        "name": "Test Race",
        "date": "2025-06-01",
        "distance_miles": 100
      }
    },
    "run_pipeline": false
  }'
```

---

## 8. Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `WOOCOMMERCE_SECRET` | Webhook secret from WooCommerce | Yes |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret (if using direct Stripe) | No |
| `ATHLETES_DIR` | Path to athletes directory | Yes |
| `SCRIPTS_DIR` | Path to scripts directory | Yes |
| `PORT` | Server port (default: 8080) | No |
| `FLASK_DEBUG` | Enable debug mode | No |

---

## 9. Checkout Flow

```
Customer visits gravelgodcycling.com/custom-training-plan
                    ↓
        Selects tier (Starter/Race Ready/Full Build)
                    ↓
            Adds to cart
                    ↓
      Checkout - fills intake form fields
                    ↓
        Stripe Checkout (payment)
                    ↓
    Order completed → Webhook fires
                    ↓
     Webhook server creates athlete profile
                    ↓
      Pipeline generates training plan
                    ↓
    Email delivers plan + dashboard link
```

---

## 10. Troubleshooting

### Webhook not firing:
- Check WooCommerce → Status → Logs
- Verify webhook URL is accessible (not behind auth)
- Check SSL certificate is valid

### Pipeline failing:
- Check server logs
- Verify all scripts are deployed
- Test with `/webhook/test` endpoint

### Email not sending:
- Verify SMTP settings in pipeline
- Check spam folder
- Review email script logs
