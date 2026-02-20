# How the Gravel God Payment System Works

*A "hurr durr" guide to the whole thing.*

---

## What Did We Build?

We built a **store** that sells three things to gravel cyclists:

| Product | What They Get | Price |
|---------|--------------|-------|
| **Training Plan** | Custom workout schedule + Zwift files for their race | $60-$249 (depends on weeks until race) |
| **Coaching** | A real human coach checks in every 4 weeks | $199-$1,200 per 4 weeks + $99 setup fee |
| **Consulting** | A one-time phone call to talk race strategy | $150/hour |

---

## The Big Picture

Here's the whole journey, start to finish:

```
    YOUR WEBSITE                     STRIPE                      YOUR SERVER
   (SiteGround)                  (handles money)                  (Railway)
  ================              ================               ================

  Athlete finds your
  coaching/training page
         |
         v
  Clicks "Buy" button
         |
         |-------- sends request -------->|
         |                                |
         |                      Creates checkout
         |                      session with price,
         |                      athlete info, etc.
         |                                |
         |<------ checkout URL -----------|
         |
         v
  Browser goes to
  Stripe checkout page
  (stripe.com)
         |
  Athlete types in
  card number:
  4242 4242 4242 4242
  (test) or real card
         |
         v
                        Stripe charges the card
                                |
                        +-------+-------+
                        |               |
                   PAID!            ABANDONED
                   (completed)      (expired after 60 min)
                        |               |
                        v               v
                   Stripe fires    Stripe fires
                   webhook to      webhook to
                   Railway         Railway
                        |               |
         +--------------+          +----+-----+
         |                         |          |
    TRAINING PLAN?            Sends recovery
    Build custom plan,        email: "Hey,
    email it to athlete       you left your
         |                    cart behind!"
    COACHING?                      |
    Log it, email coach       Includes link
    "New client!"             to resume
         |                    checkout
    CONSULTING?
    Log it, email coach
    "Schedule a call!"
         |
         v
  Athlete's browser
  redirects to YOUR
  success page on
  SiteGround
         |
    "Your plan is
     on the way!"
         |
    GA4 fires
    "purchase" event
         |
  Cross-sell: "Want
  coaching too?"
```

---

## The Three Checkout Flows (Zoomed In)

### 1. Training Plan

```
  ATHLETE                           YOU (behind the scenes)
  ========                          =======================

  Fills out questionnaire:
  - What race? (Unbound 200)
  - When? (June 7, 2026)
  - FTP? (250 watts)
  - Weight? (75 kg)
  - Hours/week? (10)
  - Weaknesses? (climbing)
          |
          v
  System calculates:
  "June 7 is 15 weeks away"
  "15 weeks x $15/week = $225"
          |
          v
  Athlete sees price,
  clicks "Get My Plan"
          |
          v
  Goes to Stripe -----------> Stripe page shows $225
                               Athlete pays
                                    |
                                    v
                               Webhook fires -----> Your server:
                                                    1. Saves athlete profile
                                                    2. Runs the AI pipeline
                                                       (takes ~5 min)
                                                    3. Generates:
                                                       - Training guide (PDF-ish)
                                                       - .zwo workout files
                                                    4. Emails everything to athlete
                                                    5. Emails YOU: "New sale!"
                                                    6. Logs to YYYY-MM.jsonl
                                                         |
                               Browser redirects         |
                               to success page           |
                               /training-plans/success/  |
                                                         v
                                                    Follow-up emails:
                                                    Day 1: "Here's how to import"
                                                    Day 3: "How's week 1?"
                                                    Day 7: "Want coaching?"
```

### 2. Coaching

```
  ATHLETE                           YOU
  ========                          ===

  Reads coaching page
  (/coaching/)
  Picks a tier:
  - Minimum: $199/4wk
  - Mid: $299/4wk
  - Maximum: $1,200/4wk
          |
          v
  Clicks tier CTA
          |
          v
  Goes to Stripe -----------> Stripe shows:
                               Line 1: Coaching ($199/4wk recurring)
                               Line 2: Setup fee ($99 one-time)
                               Total first payment: $298
                               Athlete pays
                                    |
                                    v
                               Webhook fires -----> Your server:
                                                    1. Logs it
                                                    2. Emails YOU:
                                                       "New coaching client!
                                                        Tier: min
                                                        Subscription: sub_xxx"
                                                    (no AI pipeline --
                                                     coaching is human-delivered)
                               Browser redirects
                               to /coaching/welcome/
                               "Fill out the intake form"
                               Links to /coaching/apply/
```

### 3. Consulting

```
  ATHLETE                           YOU
  ========                          ===

  Reads consulting page
  (/consulting/)
  Picks hours: 2
          |
          v
  Goes to Stripe -----------> Stripe shows:
                               2 x $150/hr = $300
                               Athlete pays
                                    |
                                    v
                               Webhook fires -----> Your server:
                                                    1. Logs it
                                                    2. Emails YOU:
                                                       "New consulting!
                                                        2 hours, schedule it!"
                               Browser redirects
                               to /consulting/confirmed/
                               "Check email for scheduling link"
```

---

## What Happens When Someone Abandons Checkout?

```
  Athlete clicks "Buy"
  Gets to Stripe page
  Gets distracted by cat video
  ... 60 minutes pass ...
          |
          v
  Stripe: "This checkout expired"
  Fires webhook to your server
          |
          v
  Your server sends recovery email:
  "Hey! Your 12-week training plan is still waiting."
  [Resume Checkout] <-- Stripe provides this link
          |
          v
  Athlete clicks link
  Back to Stripe checkout
  (same price, same everything)
  Pays this time
  Normal flow continues
```

---

## Where Does Everything Live?

```
YOUR LAPTOP
=============
gravel-race-automation/           <-- The WEBSITE stuff
  wordpress/
    generate_coaching.py          <-- Builds /coaching/ page
    generate_consulting.py        <-- Builds /consulting/ page
    generate_success_pages.py     <-- Builds 3 success pages
  scripts/
    push_wordpress.py             <-- Deploys to SiteGround
    create_stripe_products.py     <-- Documents Stripe price setup

athlete-custom-training-plan-pipeline/    <-- The BACKEND stuff
  webhook/
    app.py                        <-- THE BIG FILE (handles everything)
  run_test_server.py              <-- Local testing with fake money
  athletes/
    scripts/
      generate_full_package.py    <-- AI builds the training plan


SITEGROUND (your web host)        <-- Where athletes SEE things
=================================
  /coaching/                      <-- "Hire a coach" page
  /coaching/welcome/              <-- Success: "Welcome aboard"
  /coaching/apply/                <-- Intake questionnaire
  /consulting/                    <-- "Book a call" page
  /consulting/confirmed/          <-- Success: "Session booked"
  /training-plans/questionnaire/  <-- "Build my plan" form
  /training-plans/success/        <-- Success: "Plan incoming"


RAILWAY (your app server)         <-- Where the BRAIN lives
=================================
  /webhook/stripe                 <-- Stripe talks to this
  /api/create-checkout            <-- Training plan checkout
  /api/create-coaching-checkout   <-- Coaching checkout
  /api/create-consulting-checkout <-- Consulting checkout
  /api/cron/followup-emails       <-- Daily email sender
  /health                         <-- "Am I alive?" check


STRIPE (payment processor)        <-- Where MONEY lives
=================================
  Checkout pages (hosted by Stripe)
  Customer records
  Subscription management
  Webhook delivery + retries
```

---

## Safety Nets (So Nothing Goes Wrong)

| What Could Go Wrong | What Prevents It |
|---------------------|-----------------|
| Stripe sends the same webhook twice | **Idempotency check** -- we mark orders processed BEFORE the slow pipeline runs, so duplicates bounce off |
| Athlete's email gets logged in plaintext | **PII masking** -- `u***@e***.com` in all logs |
| Someone spams the checkout endpoint | **Rate limiting** -- 20 requests/minute per IP |
| CSS token name is wrong and page looks broken | **Preflight checks** -- validates every `var(--gg-*)` against real token definitions |
| Pipeline takes 5 minutes, Stripe times out | We return 200 eventually; Stripe retries but idempotency catches it |
| Coach misses a new sale | **Email notification** on every single purchase, even failed ones |

---

## How to Test It (Without Real Money)

**You need three terminal windows:**

```
TERMINAL 1 -- Start the test server
================================================
cd /Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline
STRIPE_TEST_KEY=sk_test_YOUR_KEY python3 run_test_server.py


TERMINAL 2 -- Forward Stripe webhooks to your laptop
================================================
stripe listen --forward-to localhost:5050/webhook/stripe


TERMINAL 3 -- Trigger a test purchase
================================================

# Training plan:
curl -X POST http://localhost:5050/api/create-checkout \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test Athlete",
    "email": "test@example.com",
    "races": [{
      "priority": "A",
      "name": "Unbound 200",
      "date": "2026-06-07",
      "distance": 200,
      "elevation": 6500
    }]
  }'

# Coaching:
curl -X POST http://localhost:5050/api/create-coaching-checkout \
  -H 'Content-Type: application/json' \
  -d '{"name": "Test Athlete", "email": "test@example.com", "tier": "min"}'

# Consulting:
curl -X POST http://localhost:5050/api/create-consulting-checkout \
  -H 'Content-Type: application/json' \
  -d '{"name": "Test Athlete", "email": "test@example.com", "hours": 2}'
```

Each curl gives you a `checkout_url`. Open it in your browser. Pay with:

| Field | Value |
|-------|-------|
| Card number | `4242 4242 4242 4242` |
| Expiry | Any future date |
| CVC | Any 3 digits |
| Name | Anything |

After paying, watch Terminal 1 -- you'll see the webhook fire and the order get processed.

---

## The Numbers

- **114 backend tests** (webhook, checkout, idempotency, emails, rate limiting)
- **76 success page tests** (SEO, GA4, brand compliance, token validation)
- **71 coaching page tests** (accessibility, billing copy, CSS tokens)
- **3 products**, **3 checkout endpoints**, **3 success pages**
- **2 webhook events** handled (completed + expired)
- **3 follow-up emails** (day 1, 3, 7 -- training plans only)
- Rate limited to **20 checkouts/minute** per IP
- Abandoned carts recover after **60 minutes**

---

*Last updated: 2026-02-20*
