# Verdict: NO-GO

The spec should not be implemented as written. I found 22 blockers. Several are direct contradictions between the stated invariants and the proposed design; several rely on capabilities the pinned code does not have; and four observed Monika defects are neither fixed nor scoped out.

## Review basis

All code evidence below is from the required refs, never the working tree. The refs resolve to the same commit:

```text
$ git rev-parse origin/main af284c2
af284c2647b20388c7bb57678fc123780f6a6660
af284c2647b20388c7bb57678fc123780f6a6660
```

I also hashed every inspected file through `git show` at both refs. The hashes matched. Representative output:

```text
$ for p in athletes/scripts/intake_to_plan.py athletes/scripts/plan_ir.py webhook/app.py webhook/fulfillment_state.py delivery/trainingpeaks/adapter.py; do for r in origin/main af284c2; do git show "$r:$p" | shasum -a 256 | awk -v ref="$r" -v path="$p" '{print ref, path, $1}'; done; done
origin/main athletes/scripts/intake_to_plan.py 83501dd3cc9842a7cfde0d13b1647025e5e50516f283c68c2108a9c90633e2cf
af284c2 athletes/scripts/intake_to_plan.py 83501dd3cc9842a7cfde0d13b1647025e5e50516f283c68c2108a9c90633e2cf
origin/main athletes/scripts/plan_ir.py 82c8d72b6659193a7a33083e6a8c470ebbeffc3a16b575db752454a5db7b7719
af284c2 athletes/scripts/plan_ir.py 82c8d72b6659193a7a33083e6a8c470ebbeffc3a16b575db752454a5db7b7719
origin/main webhook/app.py c5b7621fa89a2b4d5aceb4136a0e961802b6081ffeff92f8af5c641f4c020053
af284c2 webhook/app.py c5b7621fa89a2b4d5aceb4136a0e961802b6081ffeff92f8af5c641f4c020053
origin/main webhook/fulfillment_state.py aac7f0762d92333f5299e877b963d46c541fdd47b02f924a81bb60e52444c5b9
af284c2 webhook/fulfillment_state.py aac7f0762d92333f5299e877b963d46c541fdd47b02f924a81bb60e52444c5b9
origin/main delivery/trainingpeaks/adapter.py 028f6c1be93b1f58d6e5c133a7f1b8f465aefad5cc0d106634e579cd39cbc393
af284c2 delivery/trainingpeaks/adapter.py 028f6c1be93b1f58d6e5c133a7f1b8f465aefad5cc0d106634e579cd39cbc393
```

## BLOCKERS

### 1. The spec falsely treats the TrainingPeaks adapter as proven idempotent

> “All calls route through the existing `TrainingPeaksAdapter` (`delivery/trainingpeaks/adapter.py` — idempotent upserts keyed on manifest external IDs, durable op-log, readback verification).”

> “On partial failure: the op-log makes retry safe (no duplicate calendar objects — already the adapter's contract)”

The adapter is checkpointed, not crash-safe. It POSTs first and only then adds the key to `done` and saves the op-log. A process death after a successful POST and before `_save()` causes the next run to POST again. The code sends an `Idempotency-Key`, but there is no evidence that the undocumented TP endpoints honor it. The fake server supplies idempotency itself by deduplicating `external_id`, so the test assumes the behavior it is meant to establish.

```text
$ git show af284c2:delivery/trainingpeaks/adapter.py | nl -ba | sed -n '40,61p'
    40  def _request(...):
    43      headers = {'Authorization': f'Bearer {self.token}'}
    44      if payload and payload.get('external_id'):
    45          headers['Idempotency-Key'] = str(payload['external_id'])
    46      response = requests.request(...)
...
    57      response = self._request('POST', path, payload)
    58      self.done.add(key)
    59      self.operations[key] = ...
    60      self._save()

$ git show af284c2:athletes/scripts/test_trainingpeaks_adapter.py | nl -ba | sed -n '31,40p'
    31  def do_POST(self):
...
    37      # TP idempotency behavior represented by external ID.
    38      if not any(item.get('external_id') == data.get('external_id') for item in owner.items[bucket]):
    39          owner.items[bucket].append(data)
```

What must change: stop describing duplicate prevention as an existing contract. Specify and test a reconciliation algorithm that survives the POST/checkpoint crash window: deterministic remote lookup before write, persisted operation intents, remote object IDs, and recovery after ambiguous timeouts. If TP truly honors a key, capture and test that fact against a controlled live canary before relying on it. D3 cannot promise retry safety until then.

### 2. D1/D3 do not choose between two incompatible manifests and two incompatible apply paths

> “It exposes ... `apply(manifest)`, `verify(manifest)`.”

> “All calls route through the existing `TrainingPeaksAdapter`.”

> “Runs worker `apply(manifest)` through the adapter.”

There are two different manifests. `tp_manifest.json` has `sessions` with TP-native `structure` and is consumed by `tools/tp_apply_order.py`/the browser driver. `fulfillment_manifest.json` has `workouts` with internal `segments` and is what `TrainingPeaksAdapter.apply()` expects. The adapter does not consume `tp_manifest.json`; the current browser apply path does not use the adapter. D3 also requires threshold/zone updates, but neither manifest nor the adapter represents them.

```text
$ git show af284c2:tools/tp_apply_order.py | nl -ba | sed -n '1,18p;50,51p;237,248p'
     4  Architecture: this CLI *prepares and validates only*. It never talks to
     5  TrainingPeaks itself — ``tp_apply_driver.js`` executes inside a logged-in TP
     6  browser tab ...
     9  1. loads + validates ``tp_manifest.json`` ...
    50  MANIFEST_FILENAME = "tp_manifest.json"
...
   246      "structure": session.get("structure"),

$ git show af284c2:athletes/scripts/fulfillment_manifest.py | nl -ba | sed -n '21,39p'
    21  def build_manifest_from_plan_ir(...):
    24      workouts, notes = [], []
...
    37          'segments': session.get('segments', []), ...
    39      workouts.append(item)

$ git show af284c2:delivery/trainingpeaks/adapter.py | nl -ba | sed -n '67,88p'
    67  def apply(self, athlete_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    69      for index, workout in enumerate(manifest.get('workouts', []), 1):
...
    75          'segments': workout.get('segments', []),
```

What must change: name one canonical apply contract, its versioned schema, and its owner. Define a migration that removes or adapts the other path. Add threshold/zone operations, readback, evidence, and rollback to that schema and implementation. Do not permit both the JS browser driver and Python adapter to remain calendar-speaking authorities.

### 3. A1's no-ZWO HR/RPE path cannot produce PlanIR or a TP manifest in the pinned architecture

> “ZWO files are generated **only** for `power_basis == "measured"`. HR/RPE athletes get the TP manifest with HR-zone/RPE structured targets plus workout descriptions.”

PlanIR builds prescribed sessions by globbing ZWO files and parsing power segments from them. With no ZWOs, calendar days become synthesized rest days. Its segment schema contains only power fields, and its TP projection hardcodes `percentOfFtp`. Tests explicitly assert every non-rest bike session comes from a ZWO and every bike structure uses `percentOfFtp`. “Implementation latitude” is not enough; the proposed output has no source model.

```text
$ git show af284c2:athletes/scripts/plan_ir.py | nl -ba | sed -n '56,69p;326,365p;477,503p'
    56  @dataclass
    57  class Segment:
...
    61      power_low: Optional[float] = None
    62      power_high: Optional[float] = None
    63      power_target: Optional[float] = None
...
   326  def _tp_structure_from_segments(...):
...
   362      "primaryIntensityMetric": "percentOfFtp",
...
   483  zwo_paths = sorted((athlete_dir / "workouts").glob("*.zwo")) ...
   484  if not zwo_paths:
   485      warnings.warn("PlanIR: optional artifact missing: workouts/*.zwo", ...)
...
   500  else:
   501      # Calendar days without a rendered ZWO are real rest days ...
   503      week.sessions.append(_rest_session(day.get('date')))

$ git show af284c2:athletes/scripts/test_tp_projection.py | nl -ba | sed -n '171,176p;214,231p'
   171  # filename_stem may be None only for a PlanIR-synthesized day_off
   174  # session always comes from a real emitted ZWO in this pipeline.
   175  if s['tp_kind'] != 'day_off':
   176      assert s['filename_stem']
...
   214  # Every bike session has a structure ...
   230      assert structure['primaryIntensityMetric'] == 'percentOfFtp'
```

What must change: A1 needs an architecture section, not implementation latitude. Introduce a metric-neutral canonical workout model before rendering, with typed targets (`power`, `%LTHR`, `%HRmax`, `RPE`, free ride), then make ZWO, PlanIR, preview, both manifests, guide, polyline handling, and apply/readback project from it. Add end-to-end fixtures for HR with LTHR, HR with only HRmax, and RPE-only.

### 4. Deleting intake FTP estimation merely moves fabricated FTP into fueling

> “Estimation is **deleted**, not flagged. `ftp_watts` may be `None`.”

> “No watt figure appears in any athlete-facing artifact.”

`fueling_policy.build_fueling_prescription()` replaces null FTP with `weight_kg * 2.4`, uses it to compute the athlete-facing carb prescription, and serializes the invented FTP and “absolute work watts” as inputs. A1 does not mention changing this code. Thus the same fabricated anchor remains, only downstream and harder to see.

```text
$ git show af284c2:athletes/scripts/fueling_policy.py | nl -ba | sed -n '90,110p;148,155p'
    90  def build_fueling_prescription(... ftp_watts: Optional[float], ...):
...
   102      if not ftp_watts or ftp_watts <= 0:
   103          ftp_watts = weight_kg * 2.4
   104          assumptions.append("FTP unavailable; estimated absolute work rate from body mass.")
   105      absolute_work = float(ftp_watts) * intensity_factor
...
   152      inputs={...,
   153              "ftp_watts": round(float(ftp_watts)), ...
   154              "absolute_work_watts": round(absolute_work), ...}
```

What must change: specify a null-FTP fueling model that does not infer watts, or make fueling unavailable pending coach input. Remove watt-derived inputs from null-power artifacts and add assertions across `fueling.yaml`, guide, preview, email, PlanIR, both manifests, and ZIPs. Also rewrite guide copy that currently tells no-FTP athletes that their ZWOs use FTP and instructs them to perform an FTP test.

### 5. A blocked coach still receives the exact executable artifacts needed to bypass the gate

> “`BLOCKED_REVIEW` means the coach sees the blockers and the review controls — and nothing that lets them fulfil around the gate.”

> “The coach's *review* access (full package, `?type=full`) is never blocked.”

Those statements cannot both hold. The full package contains `workouts/` and all customer deliverables. A measured-power blocked plan therefore gives the coach importable ZWOs—the bypass observed in the handoff. Removing import instructions from email does not remove the bypass.

```text
$ git show af284c2:webhook/app.py | nl -ba | sed -n '1659,1664p;1682,1727p'
  1659  def persist_deliverables(...):
  1660      """Copy deliverables ... create zip.
  1662      Returns ... customer_zip_path ...
  1663      Customer zip excludes coach-only files ...
...
  1682      # Copy workouts/
...
  1719      # Create FULL zip (coach — everything)
  1720      full_zip = ... '-full-package.zip'
  1721      _create_zip(delivery_dir, full_zip, exclude_zip=True,
  1722                  exclude_files={'fulfillment_status.json'})
```

What must change: define a non-executable blocked-review bundle or weaken I2 honestly. For example, expose preview/brief/guide plus rendered target summaries but withhold ZWO, TP-native structures, apply jobs, and customer artifacts until APPROVED. If executable files are indispensable for review, the spec cannot claim technical prevention; it must define the remaining procedural control and audit it.

### 6. The new structural rules are assigned to a gate that runs before the defects exist

> “Each is a compliance rule with a fixture test.”

The existing compliance gate runs on the block-builder plan before any ZWO is rendered. The actual race-day, field-test, pre-plan, and other legacy overlays are emitted later. `block_compliance.py` explicitly says the full pipeline never sets the race role at that stage. `SESSION_PREDATES_ORDER` also needs the order timestamp, which `validate_plan()` does not accept.

```text
$ git show af284c2:athletes/scripts/generate_athlete_package.py | nl -ba | sed -n '753,767p;1972,2114p'
   753  # COMPLIANCE GATE — ... BEFORE any
   755  # ZWO is rendered.
...
   762  _compliance = _bb_validate(
   763      _bb_plan,
   764      target_hours=cycling_hours_target,
   765      off_days=_bb_off_days,
   766      max_intensity=max_intensity_per_week,
...
  1976  is_race_day = day_info.get('is_race_day', False)
...
  2103  _defer_to_legacy = (
  2104      is_race_day
...

$ git show af284c2:athletes/scripts/block_compliance.py | nl -ba | sed -n '78,90p;351,356p'
    78  def _week_has_race_day(...):
...
    83  The full pipeline never sets it — race days there defer to the legacy
    84  ZWO overlay AFTER this gate runs ...
...
   351  def validate_plan(plan: dict, target_hours: float = 9,
   354                    off_days: List[str] = None,
   355                    max_intensity: int = 3, ...)
```

What must change: put final-output rules in a post-render validator over PlanIR/`tp_manifest.json`, with the order-created/delivery timestamp passed explicitly. Keep only rules whose facts exist in `_bb_plan` in block compliance. Define exact semantics for race-week counting (whether notes, rest days, strength, and W00 count), duplicate field tests (FTP vs HR/RPE), and order vs delivery timestamp.

### 7. `SCHEDULE_CONTRADICTION` treats an ambiguous v1 answer as a hard prohibition

> “The generated week assigns a session type to a day the athlete explicitly designated otherwise (Monika: long-ride days Mon/Tue/Sun, yet intervals landed on Tue *and* Sun).”

The handoff's adjudicated defect says those lists are availability, not intent. The pinned parser itself turns every listed long-ride day into a broadly available, key-day-capable day; it does not record “intervals forbidden.” A rule cannot prove direct contradiction from this input. The Monika replay's required `SCHEDULE_CONTRADICTION` is therefore not a trustworthy assertion.

```text
$ git show af284c2:athletes/scripts/intake_to_plan.py | nl -ba | sed -n '1033,1077p'
  1033  long_ride_days = parse_day_list(...)
  1034  interval_days = parse_day_list(...)
...
  1064  elif day in long_ride_days:
  1065      preferred_days[day] = {
  1066          'availability': 'available',
  1068          'max_duration_min': 600,
  1069          'is_key_day_ok': True,
...
  1071  elif day in interval_days:
...
  1076          'is_key_day_ok': True,

$ sed -n '60,72p' docs/MONIKA_RENK_PIPELINE_FINDINGS.md
The root confusion: three "long ride days" inside a 7–10 h week is
arithmetically impossible, so those lists are *availability*, not intent.
```

What must change: do not hard-block on a v1 long-day/interval-day overlap. Define normalized constraint semantics and version them. The blocking rule can apply only to explicit v2 prohibitions/fixed slots; v1 ambiguity should be a confirmation item. Update the replay accordingly.

### 8. The unchanged transition endpoint cannot store the review confirmations required by I5

> “Unconfirmed items are recorded in the approval metadata (I5).”

> “the transition API ... is unchanged underneath”

The state machine stores only coach/time in `approval`. Its optional `metadata` goes only into history. More importantly, the Flask endpoint does not accept or forward `metadata` at all. Confirmation state cannot be recorded through the proposed unchanged endpoint.

```text
$ git show af284c2:webhook/fulfillment_state.py | nl -ba | sed -n '169,210p'
   169  def transition(... metadata: Optional[Dict[str, Any]] = None):
...
   185      state["approval"] = {"coach": coach.strip(), "at": now_iso()}
...
   209  _history(state, "TRANSITION", ...,
   210           coach=coach.strip(), **(metadata or {}))

$ git show af284c2:webhook/app.py | nl -ba | sed -n '2380,2401p'
  2380  @app.route('/api/fulfillment/<athlete_id>/transition', methods=['POST'])
...
  2393      state = transition_fulfillment(
  2394          ..., str(data.get('to', '')),
  2395          str(data.get('coach', '')), waiver=data.get('waiver'),
  2396          platform=..., evidence=...,
  2397      )
```

What must change: version the state schema and transition API. Store a server-validated snapshot of confirmation item IDs, values/digests, confirmed/unconfirmed disposition, revision, and reviewer identity in the approval record/history. Reject unknown or stale client-supplied item IDs. Expose the audit record via the authenticated status/review surface.

### 9. Signed-link possession cannot satisfy “named coach” provenance, and it cannot call the unchanged API safely

> “authenticated by a signed, expiring, revision-bound link”

> “no accounts/roles system (one coach; the signed link + secret is the auth model)”

> “For every delivered plan we can answer: who approved”

The current endpoint trusts a caller-supplied `coach` string after checking only the global `CRON_SECRET`. A signed email link proves possession of the link, not the human's identity; anyone to whom it is forwarded can type “Matti.” A browser cannot call the unchanged endpoint without either exposing `CRON_SECRET` to client code or adding a server-side action endpoint, which means it is not unchanged. The spec also omits CSRF/replay behavior, link revocation, TTL, nonce use, and the result of email security scanners opening links.

```text
$ git show af284c2:webhook/app.py | nl -ba | sed -n '2380,2397p'
  2380  @app.route('/api/fulfillment/<athlete_id>/transition', methods=['POST'])
  2383  secret = request.headers.get('X-Cron-Secret', '')
  2384  if not secret or not hmac.compare_digest(secret, os.environ.get('CRON_SECRET', '')):
  2385      return jsonify({'error': 'Unauthorized'}), 401
...
  2395      str(data.get('coach', '')), waiver=data.get('waiver'),

$ git show af284c2:webhook/fulfillment_state.py | nl -ba | sed -n '173,176p'
   173  if to not in VALID_STATUSES: ...
   175  if not str(coach).strip():
   176      raise FulfillmentStateError("coach is required")
```

What must change: choose an honest identity model. Either authenticate a coach principal and bind it server-side, or change I5 to record “review-link credential X” rather than a named human. Use a server-side POST action/session; never embed the global secret. Specify short TTL, revision/audience/action scopes, single-use or revocation rules, CSRF protection, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, log redaction, and scanner-safe GET behavior.

### 10. Download tokens are not artifact-scoped, so `type=customer` can be escalated to the full private package

> “Download tokens ... embed the `generation_revision`”

> “`type=full` (coach, authed) ... `type=customer` ...”

Revision binding alone is insufficient. The current same token authorizes either artifact; the caller chooses `?type=full`. If the target preserves that shape, any customer token can retrieve the coach ZIP containing profile/coaching data. The token also has no explicit expiry claim—current validation accepts current and previous month, making lifetime roughly 28–62 days despite the docstring's “30 days”—and uses the same global secret as privileged transitions.

```text
$ git show af284c2:webhook/app.py | nl -ba | sed -n '1764,1788p;2226,2255p'
  1764  def _generate_download_token(athlete_id: str) -> str:
  1767      Token = HMAC-SHA256(CRON_SECRET, athlete_id:date). Valid for 30 days.
...
  1771      payload = f'{_normalize_athlete_id(athlete_id)}:{date_str}'
...
  1779  for delta_months in (0, -1):
...
  2237  token = request.args.get('token', '')
  2239  has_token = token and _verify_download_token(athlete_id, token)
...
  2249  zip_type = request.args.get('type', 'customer')
  2252  if zip_type == 'full':
  2253      zip_path = ... '-full-package.zip'
```

What must change: bind tokens to athlete/order, exact revision, artifact type, audience, issued-at, expiry, and a key ID. Use separate signing keys for review, coach downloads, customer downloads, and transition auth. Reject unknown `type` values rather than treating them as customer. Add negative tests for customer-token→full escalation, revision mismatch, expiry boundaries, cross-athlete use, and key rotation.

### 11. D2 still cannot resolve an account under a different email

> “Before review, the worker probes by athlete email”

The handoff explicitly identifies “an account under a different email” as a critical-path case. A single `probe_athlete(email)` cannot discover or disambiguate it. The spec defines no `trainingpeaks_email`, athlete-entered TP ID, candidate selection, multiple-match behavior, or durable binding from order to TP athlete ID. D3 nevertheless proceeds as though identity is resolved.

```text
$ sed -n '210,220p;300,307p' docs/HANDOFF_CUSTOM_PLAN_FULFILMENT.md
Also unsolved: **athlete identity.** She already had an account under the coach.
A new buyer may have no account, an account under a different email, or a
dormant one with stale thresholds. Nothing today looks.
...
- **Athlete identity is on the critical path, not a footnote.** A buyer may have
  no TP account, one under a different email, a dormant one, or one not coached
  by Matti.
```

What must change: define identity inputs and resolution states. Require a unique, coach-visible TP athlete ID binding before APPROVED/APPLY; support a distinct TP email, multiple/no matches, manual selection, invite-pending, and revalidation immediately before write. Store the bound platform ID and evidence in revisioned state.

### 12. Stale or mismatched TP thresholds are soft, yet HR application depends on them

> “Dormant / stale thresholds / demographic mismatch ... | Confirmation items with both values shown”

> “Soft: they do not gate approval”

> “includes threshold/zone updates the coach confirmed in D2”

This permits approval and application with an unconfirmed age/threshold mismatch. For an HR-anchored plan, TP's threshold is what turns `%LTHR` into a prescription; using Monika's stale/wrong account values recreates the original defect. The spec never says what happens when the coach leaves the item unconfirmed, declines the update, or confirms intake values that conflict with TP.

Evidence from the pinned state machine shows approval has no confirmation precondition:

```text
$ git show af284c2:webhook/fulfillment_state.py | nl -ba | sed -n '183,201p'
   183  if to == APPROVED:
   184      if current == GENERATED:
   185          state["approval"] = {"coach": coach.strip(), "at": now_iso()}
...
   199  elif to == APPLIED:
   200      if current != APPROVED:
   201          raise FulfillmentStateError(...)
```

What must change: classify target-affecting account findings as required confirmations or blockers, not soft notices. Define resolution choices (`use TP`, `update from intake`, `manual correction completed`, `cannot resolve`) and make apply fail unless the chosen metric's prerequisite values have a resolved source and clean readback.

### 13. The permanent browser worker security design is materially incomplete and self-contradictory

> “exposes an internal, secret-authed API: `get_token()` ...”

> “No other component ever sees cookies or credentials.”

> “Credentials + TOTP seed live in a secrets store (Railway env at minimum)”

The SPA bearer is itself a credential. Exposing `get_token()` contradicts the claim that no other component sees credentials and expands compromise from one broker to every caller. The adopted prior ticket requires credential ownership, rotation, and least-privilege storage; D1 names none of those. “Internal” and “secret-authed” do not define a network boundary, TLS/mTLS, caller identity, secret rotation, request authorization, replay protection, rate limits, audit redaction, or allowed athlete IDs/actions. This service can mutate every coached athlete's calendar.

```text
$ git show af284c2:delivery/trainingpeaks/adapter.py | nl -ba | sed -n '23,47p'
    23  def __init__(self, base_url: str, token: str, ...):
    25      self.token = token
...
    43      headers = {'Authorization': f'Bearer {self.token}'}

$ git show af284c2:docs/followups/AUTOMATED_TRAININGPEAKS_FULFILLMENT_TICKET.md | nl -ba | sed -n '18,29p'
    18  ## Required follow-up specification
...
    22  - credential ownership, rotation, and least-privilege storage;
...
    26  - idempotency keys, retry/backoff behavior, and duplicate-plan prevention;
    27  - partial-application recovery and rollback;
    28  - audit logging, coach-visible failure notification, and manual fallback;
```

What must change: make the worker a credential broker that performs narrowly authorized operations without returning bearer tokens. Specify deployment/network isolation, authenticated caller identities and per-action authorization, separate rotating secrets/keys, TOTP/session rotation and recovery, egress allowlisting, payload limits, athlete/revision binding, redacted immutable audit logs, rate limits, and incident revocation. Adopt all “required follow-up specification” items, not merely the ticket's test bullets.

### 14. E1 can publish an athlete-facing artifact outside the release state and cannot revoke it on regeneration

> “One command from athlete dir → published guide ... copy to `docs/guides/<slug>/`, commit, push, poll Pages”

> “Whether guides need real privacy ... is an open coach decision”

> “No delivery instruction, customer download, or athlete-calendar write exists outside the fulfillment state machine.”

The guide is an athlete-facing deliverable at a stable public URL. E1 has no required fulfillment status, unlike E2's explicit “After `APPLIED`.” Publishing while GENERATED/BLOCKED exposes the artifact outside B2's download gate. A revision-bound ZIP token cannot invalidate a public Pages URL. `noindex` neither authorizes access nor revokes a superseded guide. The spec acknowledges the privacy risk but still places E1 in the end-to-end rollout without resolving it.

```text
$ sed -n '306,314p' docs/HANDOFF_CUSTOM_PLAN_FULFILMENT.md
- **`noindex` is not privacy.** The guide is world-readable to anyone with the
  URL on a public repo. If athlete guides should be private, they need auth or a
  private host — a meta tag only asks crawlers politely.

$ git show af284c2:webhook/app.py | nl -ba | sed -n '2249,2265p'
  2249  zip_type = request.args.get('type', 'customer')
...
  2260  return send_file(...)
```

What must change: gate publish/exposure by an explicit state and revision, or move guides behind the same scoped authorization model. Define supersession/removal on regeneration and cancellation. Resolve the privacy decision before Phase 5; it is not optional for a system that publishes health/training data.

### 15. Phase 5 deliberately leaves two athlete-facing emails active

> “likely resolution is the draft becomes the athlete-facing message and `/api/confirm` degrades to the state transition + internal receipt, but the coach picks.”

> “Phase 5 ... Gmail draft in place → coach sends → confirm.”

Today `/api/confirm` sends the customer email and only then moves APPLIED→CONFIRMED. Under the stated Phase 5 gate, the coach sends the Gmail draft and then calls confirm, which sends a second athlete-facing email. This is not a harmless copy decision; it changes exactly-once semantics and I4. The spec cannot be implemented through Phase 5 until the choice is made.

```text
$ git show af284c2:webhook/app.py | nl -ba | sed -n '2437,2459p'
  2437  @app.route('/api/confirm/<athlete_id>', methods=['POST'])
  2439  """Send "your plan is live on TrainingPeaks" email to customer.
...
  2459  return jsonify({'error': 'Plan must be APPLIED before confirmation'}), 409

$ git show af284c2:webhook/fulfillment_state.py | nl -ba | sed -n '215,234p'
   215  def confirm_after_send(...):
...
   229      if not send():
   230          raise RuntimeError("confirmation email failed")
   231      state["status"] = CONFIRMED
```

What must change: settle the flow in this spec. Define which message is athlete-facing, what event marks CONFIRMED, how send evidence is captured, and how retry/idempotency works. If Gmail remains human-sent, provide an explicit “I sent draft” transition with evidence rather than invoking an endpoint that sends again.

### 16. The Monika replay is not a reproducible or privacy-safe acceptance test

> “replay her intake as a fixture”

The raw intake is only identified on the Railway volume, the original fulfillment state is gone, and expected `RACE_STALE` depends on the mutable race snapshot. The spec does not define a frozen input bundle, order timestamp/clock, race snapshot, expected plan artifacts, or de-identification. Copying a real paid customer's intake into a public repository could expose personal/health data.

```text
$ sed -n '1,12p' docs/MONIKA_RENK_PIPELINE_FINDINGS.md
# Pipeline + intake findings from order `cs_live_a12JPpqG…` ...
...
Source of truth for the raw answers:
`/data/.intake/14478914-e6cd-47d9-85bc-c37c5038fa29.json` on the Railway volume.

$ sed -n '188,201p' docs/HANDOFF_CUSTOM_PLAN_FULFILMENT.md
A second correction: I cannot prove `RACE_STALE` was persisted for her order. Her
original `fulfillment_status.json` no longer exists ...
```

What must change: specify a synthetic/de-identified fixture checked into a non-sensitive test area, with frozen “order created at,” “generation at,” race snapshot/provenance, and exact relevant answers. Do not use her name, email, order/session ID, free-text health data, or live database lookups. State which blockers should arise in Phase 1 and which expected outputs change in Phase 3.

### 17. The hardcoded contradictory fueling table defect is absent

> “Every workstream exists to make one of these [invariants] hold.”

The Monika finding that a six-week plan printed `BASE 1-6 / BUILD 7-14 / PEAK 15-18` and a contradictory race-day range is not addressed or scoped out. A1 discusses FTP as a fueling input, not the hardcoded phase table. The pinned code still carries those fixed ranges.

```text
$ rg -ni "fueling table|GUT_TRAINING_PHASES|weeks 7-14|weeks 15-18" docs/SPEC_TRUSTWORTHY_FULFILMENT.md
[no output]

$ git show af284c2:athletes/scripts/calculate_fueling.py | nl -ba | sed -n '94,119p'
    94  GUT_TRAINING_PHASES = {
    96      "base": {
    97          "weeks": "1-6",
...
   102      "build": {
   103          "weeks": "7-14",
...
   108      "peak": {
   109          "weeks": "15-18",
...
   114      "race": {
   115          "weeks": "Race day",
   116          "target_range": [70, 90],
```

What must change: add a work item and acceptance tests that derive phase labels/ranges from the actual plan weeks and use the single canonical fueling prescription for every rendered number. The Monika replay must assert no nonexistent week bands and no cross-artifact carb contradiction.

### 18. The known polyline overshoot defect is absent and still present at the pinned commit

> “The Monika replay test ... kept forever”

Finding 10 is neither fixed nor scoped out. The current algorithm rounds each duration fraction before accumulating, explicitly allowing the cumulative x value to pass 1, then appends `[1,0]`, producing a backward tail. Tests pin the buggy golden output and do not assert monotonic bounded x.

```text
$ rg -n "polyline" docs/SPEC_TRUSTWORTHY_FULFILMENT.md
[no output]

$ git show af284c2:athletes/scripts/tp_polyline.py | nl -ba | sed -n '31,35p;54,65p'
    31  ... bookended by [0,0] and [1,0].
    32  Each step's duration fraction is rounded to 3 decimals BEFORE accumulating
    34  rounding drift can push the last cumulative point slightly past 1 ...
...
    62  cum = round(cum + round(dur / total, 3), 3)
    64  polyline.append([cum, y])
    65  polyline.append([1, 0])

$ git show af284c2:athletes/scripts/test_tp_polyline.py | nl -ba | sed -n '26,39p'
    26  def test_matches_reference_golden_vectors():
...
    34  def test_every_case_opens_and_closes_flat():
...
    39      assert len(poly) >= 3
```

What must change: include finding 10. Compute cumulative time from unrounded elapsed/total, clamp every x to `[0,1]`, enforce monotonicity, and update both vendored copies and golden fixtures. Add property tests for bounds and nondecreasing x.

### 19. The `/api/intel-stats` 24-hour observability defect is absent and still present

> “I6 — Failure is loud and closed.”

Finding 12 is neither addressed nor scoped out. The only ledger read endpoint remains fixed at 24 hours. That prevents routine auditing of older orders and undermines the operational part of “failure is loud.”

```text
$ rg -n "intel-stats" docs/SPEC_TRUSTWORTHY_FULFILMENT.md
[no output]

$ git show af284c2:webhook/app.py | nl -ba | sed -n '4022,4043p'
  4022  @app.route('/api/intel-stats', methods=['GET'])
  4025  """Last-24h commerce ground truth ...
...
  4041  now = datetime.now()
  4042  cutoff = (now - _td(hours=24)).isoformat()
```

What must change: add the tracked fix required by finding 12, including bounded/validated `hours` or `limit` pagination, authorization, deterministic ordering, and tests. If the team intentionally excludes commerce observability from this spec, name an actual tracking ticket and owner instead of omitting it.

### 20. The altitude-section failure assertion is absent

> “One command from athlete dir → published guide ... verify both URLs.”

Finding 12b required a build assertion that a resolved high-altitude race actually renders the altitude section. E1 verifies only URL availability, and no workstream adds the semantic assertion. The trigger is still conditional on a particular flattened metadata shape, the same boundary class that failed for Monika.

```text
$ rg -n "altitude section" docs/SPEC_TRUSTWORTHY_FULFILMENT.md
[no output]

$ git show af284c2:athletes/scripts/training_guide_builder.py | nl -ba | sed -n '225,249p'
   225  def _conditional_triggers(profile: Dict, race_data: Dict) -> Dict:
...
   234      meta = race_data.get("race_metadata", {})
...
   239      avg_elev = meta.get("avg_elevation_feet", 0) or 0
   240      start_elev = meta.get("start_elevation_feet", 0) or 0
   241      show_altitude = avg_elev > 5000 or start_elev > 5000
```

What must change: add a pre-release semantic guide validator: when the frozen/resolved race snapshot has start/average elevation above the threshold, the rendered guide must contain the altitude section; failure must become a blocker/state-unavailable outcome, not a warning. Cover raw snapshot→flattening→builder→render end to end.

### 21. Course mismatch is knowingly downgraded to a soft item, so the same wrong course can still ship

> “Course-level race matching ... is **out of scope** here; tracked separately. Until then, a `_derived` entry ("course matched by slug only") makes it a confirmation item.”

> “Soft: they do not gate approval”

This does not provide a safe transitional state. Once a race record has valid provenance, `RACE_STALE` disappears. A slug match prevents `RACE_UNMATCHED`, even when the athlete's distance matches no course. The remaining soft item can be ignored and the headline course distance/elevation can still anchor the plan and guide—the exact Monika defect. “Tracked separately” names no tracker, owner, or gate.

```text
$ git show af284c2:athletes/scripts/intake_to_plan.py | nl -ba | sed -n '3307,3322p'
  3307  try:
  3308      state = load_fulfillment_state(state_path)
  3309      blockers = list(state.get('blocking_issues', []))
  3310      target_match = (profile.get('target_race') or {}).get('race_match') or {}
  3311      if target_match.get('method') == 'none':
  3312          blockers.append({
  3313              'id': 'RACE_UNMATCHED',
...
  3319      provenance_issue = (profile.get('target_race') or {}).get('race_provenance_issue')
  3320      if provenance_issue:
  3321          blockers.append({'id': 'RACE_STALE', ...})

$ sed -n '151,168p' docs/MONIKA_RENK_PIPELINE_FINDINGS.md
### 13. `mammoth-tuff.json` is single-course
Carries TUFFEST (89 mi / 7,500 ft) as the race's headline vitals with no
per-course breakdown, so her 75 mi got paired with the 89-mile course's
elevation.
```

What must change: until `courses[]` exists, add a hard `COURSE_UNRESOLVED` blocker whenever an intake distance/category cannot be proved against a specific course, or omit all course-specific distance/elevation/demand facts and build only from athlete-supplied facts. Create and link the actual schema/matching ticket. Add a verified-provenance, multi-course regression fixture so the safety does not depend on `RACE_STALE`.

### 22. Whole-flow decisions are left open even though Phase 5 claims end-to-end completion

> “Refund/cancellation/regeneration-after-apply policy — needs a coach decision; the minimal invariant now is that `write_generation`'s revision bump plus B2's token binding prevents a stale artifact from shipping.”

> “Multi-brand divergence: everything above must be brand-parameterized ... but no brand-specific behavior is designed here.”

> “Weeks sold vs weeks delivered (pricing or generation must change to agree).”

> “Phase 5 ... The coach's target state.”

These are not harmless follow-ups. A revision bump clears approval/application state but does not remove already-applied TP objects, revoke a public guide, withdraw a Gmail draft, or define refund/cancellation behavior. Multi-brand sender/host/template behavior is required before E1/E2 can run safely. Weeks sold vs delivered is a paid-product correctness invariant. The spec provides no tracking IDs, owners, or gates and still labels Phase 5 end-to-end complete.

```text
$ git show af284c2:webhook/fulfillment_state.py | nl -ba | sed -n '124,148p'
   124  def write_generation(...):
   126      """Start a new generation revision, invalidating prior operator actions."""
...
   139      "status": BLOCKED_REVIEW if issues else GENERATED,
   141      "approval": None,
   143      "application": None,
   144      "confirmation": None,

$ git show af284c2:delivery/trainingpeaks/adapter.py | rg -n "delete|rollback"
[no output]
```

What must change: make these explicit prerequisites for the phases that need them. Before automated apply/publish/draft, define cancellation/refund and regeneration-after-apply state transitions, compensation/rollback, guide/draft revocation, and evidence. Define brand-specific sender identities, hosts, templates, secrets, and unknown-brand fail-closed behavior. Add a pricing/generation reconciliation gate before any paid plan can reach GENERATED. Each deferred item needs a real tracker, owner, and phase gate; Phase 5 cannot be called complete without them.

## Non-blocking findings

Completeness accounting for all findings in `MONIKA_RENK_PIPELINE_FINDINGS.md`:

| Finding | Review disposition |
|---|---|
| 1 fabricated FTP | Addressed in intent, but blocked by 3 and 4 |
| 2 fabricated equipment tokens | A2 addresses it; anchors verified |
| 3 ignored race provenance | Existing `RACE_STALE` plus B/C address it |
| 4 schedule inversion | Addressed incorrectly; blocker 7 |
| 5 structural holes | Addressed at the wrong layer; blocker 6 |
| 6 paid weeks mismatch | Still open; blocker 22 |
| 7 goal drift/stale rationale | Explicitly deferred with Questionnaire v2/archetype-selection work; the tracker itself remains NO-GO |
| 8 hardcoded fueling table | Omitted; blocker 17 |
| 9 hardcoded `percentOfFtp` | Addressed in intent, but blocked by 2 and 3 |
| 10 polyline overshoot | Omitted; blocker 18 |
| 11 race-day structure | Already closed in pinned code; non-blocking finding 3 below |
| 12 fixed 24-hour intel endpoint | Omitted; blocker 19 |
| 12b missing altitude section | Omitted; blocker 20 |
| 13 single-course race model | Unsafe deferral; blocker 21 |

1. The pinned anchors are generally accurate. FTP fabrication (`829-842`), device splitting (`506-508`), late blocker assembly (`3307-3330`), state-write warning (`3340-3345`), webhook success branching (`2011-2025`), download (`2226-2266`), order status (`2280`), transition/status (`2381`/`2404`), and confirm (`2437-2459`) all resolve to the described code.

2. The state machine's existing hard gates are real: complete waiver equality is enforced at `fulfillment_state.py:187-195`, APPLIED requires APPROVED at `:199-203`, and `confirm_after_send` requires APPLIED and serializes exactly-once sending.

3. Finding 11 (“race day should never carry a structure”) is already closed at the pinned commit for the TP-native projection. `test_tp_projection.py:269-275` asserts `structure is None` for `race`, and `plan_ir.py:422-424` only creates a structure for `tp_kind == "bike"`.

4. The spec correctly fixes the handoff's earlier false statement that the gate itself does nothing. Its narrower claim—that notification/download/manual artifacts route around it—is supported.

5. The broad `_derived` registry is directionally useful, but its schema needs stable IDs, sensitivity labels, source timestamps, versioning, and explicit distinction among measured, athlete-reported, defaulted, inferred, and externally observed values. This becomes blocking if it is not resolved as part of blockers 3, 8, and 12.

6. Phase 0 should specify whether “Delete `plan-truth-fixes` and `plan-ir-v0`” means local branches, remote branches, or both. Branch deletion is not required to implement the pipeline and should not be an acceptance gate.

7. A real-order regression fixture should be retained in principle, but only in the frozen, synthetic/de-identified form required by blocker 16.

## Could not verify

1. I could not verify the claimed live TrainingPeaks acceptance/round-trip behavior for `percentOfThresholdHr`, `percentOfMaxHr`, or `rpe`. The referenced `build_tp_bodies.py` is in another repository and is not present at `af284c2`; no live TP credentials or captured response fixture is available here. The new metric-neutral schema must not be approved on the handoff statement alone.

2. I could not verify any real TrainingPeaks guarantee for `Idempotency-Key` or persisted `external_id`. The local fake server implements its own deduplication, as described in blocker 1.

3. I could not replay Monika's raw intake. The findings identify it only on a Railway volume, and the handoff says her original state file is gone. This is why blocker 16 requires a frozen replacement fixture.

4. I could not verify the browser worker's ability to refresh TP sessions, perform TOTP, probe coaching relationships, update thresholds/zones, or roll back live calendar objects. None of that implementation exists in the pinned repository.

5. I could not verify TrainingPeaks terms-of-service acceptability. The spec records this as an accepted business risk, but no legal/contractual evidence is included.

6. I could not verify deterministic guide PDF rendering, Pages deployment credentials/concurrency, Gmail OAuth consent/refresh-token setup, or attachment creation. Those systems are not implemented at the pinned commit.

7. `docs/QUESTIONNAIRE_V2_SPEC.md` is present only in the local dirty working tree, not at `af284c2` (`git show af284c2:docs/QUESTIONNAIRE_V2_SPEC.md` returns “path ... exists on disk, but not in `af284c2`”). I read it for completeness context only and made no pinned-code claim from it. It remains NO-GO per the handoff, so it is not yet an actionable closure for the intake gaps.
