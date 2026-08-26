# Coaching legal review packet

> **DRAFT REQUIREMENTS PACKET — NOT AN AGREEMENT, WAIVER, OR SIGNATURE FORM.**
> This document records business facts, source conflicts, and decisions for
> licensed legal review. It must not be shown for athlete acceptance or used to
> satisfy the `coaching_agreement` or `data_consent` gates.

Prepared: 2026-08-25

## Objective

Produce one reusable adult endurance-coaching document set for Gravel God
Cycling, Roadie Labs, and XC Ski Labs. The final documents must match the
actual commercial offer, remote coaching workflow, insurance, data systems,
and athlete jurisdiction. Cycling and cross-country skiing should use separate
risk schedules under the same core services agreement when counsel permits.

The USA Cycling membership/event release supplied by the owner is an
issue-spotting reference only. Do not reproduce its language. Its consideration,
events, releasees, on-site medical treatment, anti-doping rules, media grant,
and governing structure do not describe this coaching service. USA Cycling's
published site terms also restrict commercial reproduction of its content:
https://usacycling.org/terms

## Facts supported by current code and provider readback

### Brands and offer

All three brands currently share this offer:

| Tier | Price | Current public service description |
|---|---:|---|
| Min | $199 every 4 weeks | Weekly training review; file analysis; quarterly strategy calls; structured workouts; race-day nutrition plan; custom training guide |
| Mid | $299 every 4 weeks | Everything in Min; detailed file analysis; every-4-week strategy calls; weekly plan adjustments; direct-message access; blindspot detection |
| Max | $1,200 every 4 weeks | Everything in Mid; daily file review; on-demand calls; race-week strategy; multi-race season planning; priority response |

- The billing period is 28 days, producing 13 billing cycles per year.
- TrainingPeaks Premium is represented as included with every tier.
- Checkout contains a one-time $99 setup-fee price.
- The $99 setup fee is charged by default. The public `NOSETUP` promotion code
  was deactivated on 2026-08-25 with zero redemptions. A fixed-$99, once-only
  Stripe coupon remains available for backend-only, coach-approved case-specific
  waivers; athletes are not shown a code or promotion-code field.
- Current public terms say cancellation is allowed at any time, access
  continues through the paid four-week cycle, there is no cancellation fee,
  and no refund is issued for a partially completed coaching cycle.
- Payment is processed by Stripe only after fit, identity, health disposition,
  agreement, and data-consent gates pass.
- TrainingPeaks connection and Premium activation remain separate verified
  gates after payment.

### Current delivery and data systems

The intended production flow uses or may use:

- brand websites and browser local storage for draft questionnaire answers;
- Cloudflare Worker for authenticated intake forwarding;
- Railway persistent storage for the private onboarding case;
- Resend and email for transactional messages;
- Stripe for subscription payment;
- TrainingPeaks for training history, calendar delivery, workouts, and Premium;
- Google Drive, Docs, and Sheets for restricted coaching operations;
- Gmail and Messages for communications where selected;
- AI-assisted processing for intake analysis, coaching review preparation, and
  plan proposals, subject to coach approval.

The current privacy pages name FormSubmit as the coaching-form processor. That
will be inaccurate after the new intake route is deployed and must be replaced
with approved language covering the real processors, purposes, access,
retention, deletion, and athlete choices.

## Owner decisions recorded 2026-08-25

- Public response target: applications are reviewed and answered usually
  within two business days.
- Commitment language: “No long-term commitment”; coaching renews every four
  weeks, cancellation must occur before the next renewal, access continues
  through the paid cycle, and there is no cancellation fee.
- Setup fee: charged by default; waivers are private and case-specific.
- Minors: athletes age 13–17 use a separate parent/legal-guardian contact and
  signature gate. The public intake contact fields do not constitute consent.
  The current path rejects athletes under 13 pending separate child-privacy and
  jurisdiction review.

## Remaining business-language decisions

These are not legal drafting questions. The owner must choose the actual
service before counsel can document it.

1. **Daily and priority response.** Define whether "daily" includes weekends
   and holidays and whether "priority response" has a measurable response
   window.
2. **Direct-message access.** Define approved channels, ordinary response
   expectations, quiet hours, and the fact that messaging is not emergency
   monitoring.
3. **On-demand calls.** Define reasonable-use, scheduling, cancellation, missed
   call, and rescheduling rules.
4. **Subscription start.** Decide whether the first 28-day cycle and coaching
   duties begin at checkout, the desired start date, or confirmed platform
   readiness.
5. **TrainingPeaks Premium.** Define when Premium begins and what happens when
   coaching ends, pauses, payment fails, or TrainingPeaks changes its offer.
6. **Pause policy.** Define whether injury, travel, off-season, or clinician
   restriction can pause billing or service.

## Document set to approve

### 1. Core coaching services agreement

The approved template needs to state:

- exact legal provider identity, address, and brand/DBA relationship;
- selected tier and incorporated service schedule;
- start date, 28-day automatic renewal, price, taxes if applicable, setup fee,
  promotion, payment failure, cancellation, pause, and refund rules;
- coach and athlete responsibilities;
- communication channels and service expectations;
- scheduling and missed-call rules;
- no guaranteed performance, race result, selection, or health outcome;
- ownership and permitted personal use of plans, workouts, guides, and files;
- suspension and termination conditions;
- interaction with the separate risk, health, privacy, and e-sign documents;
- the counsel-approved dispute, governing-law, venue, liability, and survival
  provisions listed below.

### 2. Adult informed consent, assumption of risk, waiver, and release

Counsel should adapt the relevant *concepts*, not USA Cycling's wording, to the
actual service:

- remote endurance coaching and athlete-controlled execution environment;
- outdoor cycling or skiing, indoor training, strength work, field testing,
  fatigue, weather, traffic or trail users, terrain, falls, collisions,
  equipment failure, and foreseeable and unknown inherent risks;
- athlete responsibility for route choice, conditions, legal compliance,
  appropriate equipment, and stopping when unsafe;
- the distinction between inherent-risk acknowledgement and any release of
  provider negligence;
- exact protected parties tied to the real provider and insurance policy;
- exclusions that cannot or should not be waived.

The following may not be imported without an express legal decision: release
of negligence, indemnity/defense obligations, covenant not to sue, arbitration,
class-action waiver, limitations period, liability cap, and fee shifting.

### 3. Health disclosure and clinician-clearance policy

The approved policy needs to explain:

- coaching is not diagnosis, treatment, rehabilitation, or emergency care;
- the athlete must provide accurate material health and injury information;
- disclosed facts are classified only under an approved policy as clear,
  needs-question, or needs-clinician-clearance;
- the coach may pause or decline training pending appropriate clinical input;
- a waiver never substitutes for medical clearance;
- emergency symptoms are outside coaching and require appropriate emergency or
  clinical care;
- what clinician receipt is sufficient and how it is retained.

### 4. Privacy, data-processing, communications, and e-sign consent

The approved notice and consent need to cover:

- each actual data source and processor listed above;
- questionnaire, training, wellness, communications, payment metadata, and
  optional health/injury data;
- purposes, access controls, AI-assisted processing, human approval, retention,
  deletion, correction, exports, incident response, and cross-border issues;
- transactional versus optional marketing communications;
- consent to electronic records, how to obtain a copy, how to withdraw consent,
  and the required hardware/software disclosures;
- retrievable and reproducible signed records under the E-SIGN framework:
  https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title15-section7001&num=0&edition=prelim

Do not bundle optional testimonial, publicity, or marketing consent with the
required coaching documents.

### 5. Minor/guardian packet, only if minors are offered coaching

This requires a separate signer and jurisdiction path. Colorado Revised
Statutes section 13-22-107 permits certain informed parental waivers of a
child's prospective negligence claim but does not extend to willful, wanton,
reckless, or grossly negligent conduct. Other jurisdictions may differ:
https://leg.colorado.gov/sites/default/files/images/olls/crs2024-title-13.pdf

The adult form, adult signature, or age field cannot substitute for verified
guardian identity and signature.

## Express legal decisions requested

Return an approved answer and operative language for each item:

| Decision | Required answer |
|---|---|
| Provider identity | Exact legal name, entity type, address, and authorized DBAs |
| Governing law | State law appropriate to provider and multistate athletes |
| Venue | Court location and any small-claims treatment |
| Dispute resolution | Court, informal escalation, arbitration, class waiver, or combination |
| Negligence release | Whether allowed, scope, conspicuousness, and jurisdiction limits |
| Indemnity | Include, narrow, or omit; defense costs and third-party claims |
| Liability limitation | Include, cap, exclusions, and interaction with insurance |
| Minors | Adult-only or approved guardian/minor documents by jurisdiction |
| Health-data rules | Applicable consumer-health, breach, and retention requirements |
| E-sign | Required consumer disclosures and acceptable signature evidence |
| Renewal/cancellation | Required subscription disclosures and re-consent triggers |
| Insurance | Confirm every protected party/activity matches the policy |
| Accessibility | Presentation and signature accessibility requirements |
| Retention | Signed documents, health receipts, case records, deletion holds |

## E-signature and onboarding acceptance criteria

For each required document, the production system must store:

- immutable template ID, version, and effective date;
- athlete legal name and verified identity binding;
- applicable jurisdiction and adult/guardian path;
- required signer identities and roles;
- affirmative electronic-record consent;
- presented document hash or provider document ID;
- signed timestamp and completed provider receipt/audit trail;
- retrievable signed-document location with restricted access;
- supersession and re-consent status.

The pipeline may advance the current gate only when:

- `coaching_agreement = signed` with `document_version` and `receipt_id`;
- `data_consent = signed` with `document_version` and `receipt_id`;
- for a minor, `guardian_consent = signed` with a document version, receipt ID,
  signer name, signer email matching intake, and parent/legal-guardian role;
- any `health_clearance = cleared` has a clinician `receipt_id`;
- no identity, jurisdiction, template-version, or signer mismatch remains.

Application submission, a typed name in a form, payment, or a general privacy
link is not a signature receipt.

## Approval block

The reviewer should return:

1. final documents in reproducible electronic form;
2. template IDs, versions, effective dates, and jurisdictions;
3. a signed approval record identifying the approving attorney and date;
4. explicit answers to every decision in the table above;
5. required public-site copy corrections;
6. required insurance or operational changes;
7. re-consent and retention rules.

Only those approved artifacts may be wired into the e-signature and payment
handoff. This requirements packet itself never satisfies a legal gate.
