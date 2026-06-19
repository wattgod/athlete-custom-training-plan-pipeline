# Improvement backlog — crank-v2

**Quality 2.22** · avg coach 5.75/10 · contract pass 67% · load 9.67/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Venue is completely fabricated: the guide states '2026: Niseko, Hokkaido, Japan' for the UCI Gran Fondo Loutraki, which is a Greek race held in Loutraki, Greece. This is a blatant factual error that will immediately destroy athlete trust.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout: the athlete is an MTB rider but multiple sections contain gravel-racing copy ('Gravel racing requires both — you need to grind up climbs and spin on flats,' 'race simulations … group rides … being on the bike for 6+ hours,' 'Road Skills' section listed in the table of contents). No MTB-specific content (trail skills, technical descending, body position, tyre pressure) is mentioned.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Indoor workout guidance tells the athlete to prepare for '6+ hours' on the bike outdoors, but the race is 69.6 miles and the fueling section estimates 4.3 h duration. The 6+ hour reference is copy-pasted from a longer-event template and directly contradicts this athlete's race data.

### 4. [critical] ×1  (road/veteran_podium_chaser)
> Gravel-specific coaching cue injected into a road plan: Section 6 (Workout Execution) states 'Gravel racing requires both — you need to grind up climbs and spin on flats.' This athlete is a road racer targeting a road Gran Fondo. 'Gravel racing' is the wrong discipline and should never appear in this document.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> Section 6 also recommends outdoor practice for 'skills practice' with the rationale of preparing for '6+ hours' on the bike, yet the race is 85 miles with an estimated ~3.9 h duration per the fueling JSON. The 6+ hour framing is inconsistent with the athlete's actual race and may cause over-preparation anxiety or wrong pacing expectations.

### 6. [major] ×1  (mtb/weekend_warrior)
> The Zone 3 power band (113–130 W) upper-bounds to 87% FTP, but the GS/Sweet Spot band starts at 88% FTP (131 W). The percentage labels leave a 1 W gap between zones that could confuse athletes using a power meter — minor arithmetic slippage but looks sloppy.

### 7. [major] ×1  (mtb/weekend_warrior)
> Long ride peak duration stated as '2.1–3.5 hours' in the Weekly Structure section. The lower bound of 2.1 h seems low for a 4.3 h race target, and the upper bound of 3.5 h is never cross-referenced to the plan's per-day cap or TSS checks — the athlete has no context for where these numbers came from.

### 8. [major] ×1  (mtb/weekend_warrior)
> The guide refers to a 'Road Skills' chapter in the table of contents, which is inappropriate for an MTB discipline. MTB-specific skills (cornering, braking technique, line choice, technical climbing) are entirely absent.

### 9. [major] ×1  (gravel/ambitious_first_timer)
> Zone distribution is stated as '80% easy / 0% tempo / 20% hard' but Polarized 80/20 is an 80/20 split (easy/hard) that simply minimises Zone 3 — it is not literally 0% tempo. The plan itself later prescribes tempo efforts in Build, so the guide contradicts its own phase progression section. This will confuse athletes who see tempo in the calendar and wonder if it's a mistake.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> Long ride ceiling in the Weekly Structure section reads '4–6.8 hours.' A 45-mile gravel race at the athlete's likely pace is approximately 3.5–4.5 hours, so 6.8 hours is significantly beyond race duration and inconsistent with a 'finish' goal on 11 h/week. The fueling section correctly cites 3.8h expected duration, making the 6.8h figure an internal contradiction that will worry the athlete.

### 11. [major] ×1  (road/veteran_podium_chaser)
> Zone table is incomplete: Zone 1 (Active Recovery) has no HRmax% listed, and Zone 6 (Anaerobic) lists 'N/A HRmax' with no RPE range shown in the table — yet every other zone has all fields populated. This looks like a generation error and undermines the professionalism of the zone reference card.

### 12. [major] ×1  (road/veteran_podium_chaser)
> The preview check shows TSS Progression as WARN, but the guide text contains no acknowledgment, explanation, or caveat to the athlete about any unusual TSS ramp. A paying podium-chaser deserves to know if their ramp rate is atypical, or the WARN should be resolved before sending.

### 13. [major] ×1  (gravel/ambitious_first_timer)
> The table of contents lists a 'Road Skills' section. This athlete is racing gravel, not road. If that section contains road-specific skills content (e.g., road cornering, peloton positioning, road sprinting) rather than gravel-specific skills (loose surface cornering, technical descending, tubeless flat repair, gravel-specific group dynamics), it is wrong-discipline content that will confuse or mislead the athlete. The section title alone is a red flag that must be verified and corrected to 'Gravel Skills' at minimum.

### 14. [major] ×1  (gravel/ambitious_first_timer)
> The intensity distribution stated in the guide is '50% easy / 35% tempo / 15% hard.' The preview check flagged Zone Distribution as WARN. A Sweet Spot / Threshold methodology for a 7 h/week athlete should sit closer to a polarized-adjacent pyramid (more Z2, moderate sweetspot/threshold, minimal Z5+), not a tempo-heavy 35% tempo split. 35% tempo risks the exact 'gray zone' overload the guide itself warns against on the very next page — this internal contradiction is embarrassing and the distribution should be reconciled with the methodology description.

### 15. [minor] ×1  (mtb/weekend_warrior)
> Weight (152 lbs / 68.9 kg) and height (5'1") appear in the guide but were not present in the provided athlete JSON — these values could not have been verified and may be placeholder or hallucinated data.

### 16. [minor] ×1  (mtb/weekend_warrior)
> '7 Years Riding' at 'Intermediate level' appears in the guide but the athlete JSON contains no experience field — this label was generated without source data and could be wrong.

### 17. [minor] ×1  (mtb/weekend_warrior)
> The countdown '149 days from today' is a rendered value that will be stale the moment the email is delayed; it should either be omitted or calculated from a fixed reference date to avoid confusing athletes who open the email days after generation.

### 18. [minor] ×1  (gravel/ambitious_first_timer)
> The 'Countdown: 100 days from today' field is a dynamic value that appears to have been computed relative to plan generation date, not the plan start date of 2026-06-29. It should either be omitted or labelled clearly so it doesn't confuse athletes reading the guide days or weeks after it was generated.

### 19. [minor] ×1  (gravel/ambitious_first_timer)
> Recovery nutrition prescription cites '28g protein + 71–85g carbs within 30 minutes' but attributes it to '71kg body weight.' The athlete's weight in the profile is listed as 157 lbs (71.2 kg), which is consistent — but the carb range (71–85g) is unusually narrow and the protein figure (28g) is on the low end of evidence-based recommendations (typically 0.4g/kg = ~28g is acceptable, but many guides cite 30–40g). Not wrong enough to block sending, but worth a coach review.

### 20. [minor] ×1  (road/veteran_podium_chaser)
> The guide refers to the athlete's experience as 'Intermediate level' in the methodology rationale section, which conflicts with the persona label 'Experienced racer chasing a podium' (veteran_podium_chaser) and the stated 17 years of riding. This mislabeling could undermine athlete confidence in the plan's calibration.

### 21. [minor] ×1  (road/veteran_podium_chaser)
> Zone 3 HRmax% (84-94%) and Zone GS HRmax% (92-96%) overlap significantly, and the GS zone's HRmax lower bound (92%) sits inside Zone 3's range. While the power boundaries are correct, the overlapping HR guidance could confuse a rider who uses HR as their primary metric.

### 22. [minor] ×1  (gravel/ambitious_first_timer)
> The zone chart states Zone 4 (Threshold) is 'sustainable for about 1 hour all-out,' which is the standard FTP definition. However, the FTP test protocol uses a 20-minute effort × 0.95, which is correct — but the guide never explains why 20 minutes × 0.95 ≈ 1-hour power. For a first-timer this creates confusion ('if FTP is 1-hour power, why am I only testing for 20 minutes?'). A single bridging sentence would close this gap and avoid undermining trust in the protocol.

### 23. [minor] ×1  (gravel/ambitious_first_timer)
> The guide mentions the long ride peak duration as '2.1-3.5 hours' in the Weekly Structure section. For an 87-mile gravel race estimated at ~5.4 hours (as used in the fueling section), a maximum long ride of 3.5 hours is on the low end. While the preview check passed Long Ride vs Race Duration, the explicit mention of this range in the narrative may set a false expectation for the athlete that their longest ride will feel race-representative — worth softening the language or adding a brief note that the final long ride is intentionally shorter than race duration by design.
