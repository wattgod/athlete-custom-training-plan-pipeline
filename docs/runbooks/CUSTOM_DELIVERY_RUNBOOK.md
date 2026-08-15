# Custom-order delivery runbook (manual, until SPEC_DELIVERY_LAYER ships)

Written after the Guillermo Romero order (2026-08-14), where the pipeline's
approved output was delivered as-is and the coach rejected it. The raw
generator output is NOT the product. Until `DeliveryIR` + `delivery_lint`
exist (see `docs/SPEC_DELIVERY_LAYER.md`), every custom order gets this
manual pass.

## The bar

The current house-standard is the most recently hand-upgraded live athlete
calendar — as of Aug 2026, Monika Renk (TP 2947583). **Diff against the live
calendar, not memory or old notes — the standard ratchets with every
hand-build.** Dump it first:

    GET fitness/v6/athletes/{id}/workouts/{start}/{end}
    GET fitness/v3/athletes/{id}/calendarNote/{start}/{end}

"Delivered" means indistinguishable in kind from that reference.

## Delivery checklist (each item was missing on a real shipped order)

1. **Titles carry dimensions**: `{Name} - {set} - {NNmin} - RPE{n}`; name
   must describe the emitted level's content, never the archetype's terminal
   form ("3x15 Tempo" containing 3x8 is a lie — retitle it).
2. **ifPlanned** set on every structured ride.
3. **No blank dates, ever**: explicit Day Off cards (type 7) on all rest
   days, including race-week gaps and the day after the race.
4. **The note series** (bodies templated from the reference dump): START
   HERE (guide URL + account-settings fixes + how-the-week-works), weekly
   briefings, AFTER TODAY'S TEST, FUELLING ladder, ALTITUDE/heat when the
   race qualifies, GRAVEL GRIT 1–4, CHECK-IN, REHEARSAL DEBRIEF, RACE WEEK,
   AFTER with the what's-next nurture close.
5. **Fuel ladder, not a flat rate**: rungs on the dated long rides climbing
   to race rate; final pre-taper sim at race rate; "where a workout quotes a
   different number, the ladder wins."
6. **Hydration is drink-to-thirst** + sodium + finish-lighter-never-heavier.
   Never "don't wait until thirsty" / "clear urine" (EAH).
7. **Race day carries no structure** (head units ERG a structured range);
   duration/TSS from stated values; course-ambiguity rendered as a decision
   rule the athlete can apply.
8. **Race week**: sharpener early week (Stars In Your Eyes class), **openers
   the day before the race**, rest days as cards.
9. **Taper keeps the legs awake**: 30/15s, cadence work, alactic bursts —
   never five flat Z2 rides.
10. **Sims mimic the race** (Act 1 punchy start / Act 2 grind with
    low-cadence climbing / Act 3 structured finale), second sim = full dress
    rehearsal at race fuel rate.
11. **Short plans skip intro levels**: an experienced athlete's only VO2 day
    must not be a Level-1 dose (check every quality session's level).
12. **Guide hosted**: `docs/guides/{athlete-id}/` on main → Pages at
    intake.gravelgodcoaching.com; noindex; PDF link after the h1.

## Verify like you mean it

Field reconciliation (36/36 dates/titles/TSS) proves transport, not quality.
After reconcile, ask the reference question: "would this survive being put
next to the standard calendar?" Then API read-back + screenshot of week 1,
one mid week, race week.

## Landmines

- **Canonical fulfillment state = `/data/deliveries/orders/<order>/fulfillment_status.json`.**
  The copy under `order-work/<order>/athletes/<id>/` is generation-time
  scratch; transitions against it fail with "requires APPLIED".
- TP notes API needs the ~791-char tpapi Bearer (sniff on reload); a shorter
  token on the page belongs to another service and 401s.
- Note delete uses the object's `id` (not `calendarNoteId`); always
  reconcile notes by (date, title) after any replace.
- APPROVED→APPLIED via the transition endpoint sends no email; CONFIRMED via
  `confirm_after_send(path, send, metadata)` — pass a no-op sender and record
  the real coach-sent email's message id when the email went out by hand.
- TP strips leading whitespace in descriptions; author flush-left.
- Structured ranges midpoint on head units; percentOfFtp needs the athlete's
  TP threshold sane — check `fitness/v1/athletes/{id}/settings` first.
