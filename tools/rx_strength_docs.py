#!/usr/bin/env python3
"""Workstream C: template -> StructuredStrength (rx) PUT-body document builder.

Pure-Python, no network. Parses the 7 reference strength session templates
(`gravel-god-training-plans/strength_builder/session_templates_text.json`,
embedded verbatim below for portability/testability -- this module must not
depend on a sibling repo's on-disk layout) into rx "StructuredStrength" PUT
request bodies, per SPEC_tp_native_custom_plans.md "Strength (D3)" and
V2_BUILD_SPEC.md's template -> blocks mapping.

Shape reference: `structured_strength_PUT_payload.json`'s inner "workout"
object is byte-for-byte the same shape as the flat PUT/save request bodies
captured in `plan_day_capture_netlog.json` -- that flat shape is what
`build_strength_doc()` returns (the PUT request body IS the raw doc; there is
no outer library-item wrapper).

Catalog-gap policy (Matti-approved, 2026-07-17): "nearest equivalent + notes".
    - exact catalog title match            -> that exercise id
    - fuzzy (best available candidate)      -> chosen id + original text/cues
                                                in the prescription's coachNotes
    - truly absent from the 690-exercise
      catalog dump                          -> `{"custom": "<canonical title>"}`
                                                placeholder; the CLI (a separate
                                                workstream) creates the custom
                                                exercise once and resolves the
                                                placeholder to a real id.

WARMUP/COOLDOWN blocks never carry prescriptions (Matti policy: prefer
coachNotes for warmup/cooldown mobility work even where a catalog id exists);
their movement list becomes the block's coachNotes text. ZERO EQUIPMENT and
NOTES are not blocks at all -- their text folds into the doc-level
`instructions` field, verbatim, minus any non-gravelgodcycling.com link.

See the bottom of this file for the reviewable movement -> catalog MAPPING
tables (EXACT_MAP / FUZZY_MAP / CUSTOM_CANONICAL) called out by the spec.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

__all__ = ["build_strength_doc", "custom_exercises_needed", "TEMPLATE_KEYS"]

# ---------------------------------------------------------------------------
# 1. Source templates -- verbatim copy of session_templates_text.json values
#    (machine-transcribed via repr() from the source JSON to guarantee
#    byte-for-byte fidelity; do not hand-edit without regenerating the same
#    way from the source file).
# ---------------------------------------------------------------------------
SESSION_TEMPLATES: Dict[str, str] = {
    'Foundation (A)': "STRENGTH — Foundation Phase\nSession A | Plan Week 2, Monday | RPE 5-6 | ~40 min\nMovement quality before load. Equipment: Bodyweight, bands, light DB/KB\n\n★ WARMUP (10 min) → All demos: gravelgodcycling.com/demos\n  • Downward Dog Lunge + Rotation ─ 5/side\n  • Tripod Bridge ─ 5/side\n  • Curtsy Lunges ─ 10/side\n  • Lateral Lunges ─ 10/side\n\n★ PREP (5 min) │ 2 rounds │ 60s rest\n  • Hip Rails ─ 10/side\n  • MiniBand Marches ─ 10/side\n  • Monster Walk ─ 10/direction\n\n★ MAIN 1: Squat Pattern │ 3 sets │ 90s rest │ RPE 6\n  A1 Goblet Squat OR Bulgarian Split Squat ─ 10 reps or 10/side\n     → Goblet: https://www.youtube.com/watch?v=MeIiIdhvXT4\n     → BSS: https://www.youtube.com/watch?v=2C-uNgKwPLE\n  A2 Push-Up + Shoulder Tap ─ 10-12 reps\n     → https://vimeo.com/111473395\n\n★ MAIN 2: Core + Carry │ 3 sets │ 90s rest │ RPE 6\n  B1 Dead Bug (add light weight) ─ 10-12 reps\n     → https://vimeo.com/111109110\n  B2 Suitcase Carry (single side) ─ 10-12 reps\n     → https://vimeo.com/111545001\n\n★ COOLDOWN (5 min) → All demos: gravelgodcycling.com/demos\n  • Deep Squat Sit ─ 60 sec\n  • Hip Flexor Stretch ─ 45 sec/side\n  • Pigeon Pose ─ 45 sec/side\n\n★ ZERO EQUIPMENT (Hotel/Travel)\n  • Goblet Squat/BSS → Air Squat or BW Split Squat\n  • Push-Up + Tap → Same\n  • Dead Bug → Same\n  • Suitcase Carry → High-Knee March 30 sec/side\n\n★ NOTES\n  Final Red phase. Testing readiness for Yellow.\n  If goblet squat + push-up feel solid → you're ready.\n  → Full guide: https://gravelgodcycling.com/strength\n\nMasters, consistency beats intensity. Show up.",
    'Foundation (B)': "STRENGTH — Foundation Phase\nSession B | Plan Week 2, Thursday | RPE 5-6 | ~40 min\nMovement quality before load. Equipment: Bodyweight, bands, light DB/KB\n\n★ WARMUP (10 min) → All demos: gravelgodcycling.com/demos\n  • Cat-Cow ─ 10 reps\n  • World's Greatest Stretch ─ 5/side\n  • Lying Windshield Wipers ─ 10/side\n  • Bird Dog (hold 3 sec) ─ 5/side\n\n★ PREP (5 min) │ 2 rounds │ 60s rest\n  • Glute Bridge (banded) ─ 10-12 reps\n     → https://vimeo.com/111033887\n  • Band Pull-Apart ─ 10-12 reps\n     → https://vimeo.com/111033315\n  • Good Morning (light) ─ 10 reps\n     → https://www.youtube.com/watch?v=1i5KDf3k8Yg\n\n★ MAIN 1: Hinge Pattern │ 3 sets │ 90s rest │ RPE 6\n  A1 KB/DB RDL (moderate load) ─ 10-12 reps\n     → https://vimeo.com/111121974\n  A2 Single-Arm DB Row ─ 10-12 reps\n     → https://vimeo.com/111523514\n\n★ MAIN 2: Glute + Anti-Rotation │ 3 sets │ 90s rest │ RPE 6\n  B1 Single-Leg Glute Bridge (banded) ─ 10-12 reps\n     → https://vimeo.com/111546505\n  B2 Pallof Press (walk-out) ─ 10-12 reps\n     → https://vimeo.com/111469204\n\n★ CORE (8 min) │ 2 rounds │ 60s rest\n  C1 Side Plank w/ Hip Dip ─ 10-12 reps\n     → https://vimeo.com/111522888\n  C2 Bird Dog (opposite reach) ─ 10-12 reps\n     → https://vimeo.com/111048715\n  C3 Dead Bug ─ 10-12 reps\n     → https://vimeo.com/111109110\n\n★ COOLDOWN (5 min) → All demos: gravelgodcycling.com/demos\n  • 90-90 Hip Stretch ─ 45 sec/side\n  • Supine Hamstring Stretch ─ 45 sec/side\n  • Thread the Needle ─ 5/side\n\n★ ZERO EQUIPMENT (Hotel/Travel)\n  • KB/DB RDL → Good Morning (BW)\n  • Single-Arm DB Row → Superman Pull\n  • Single-Leg Glute Bridge → Same\n  • Pallof Press → Isometric brace\n\n★ NOTES\n  Ready for Yellow. RDL form should be locked in.\n  If hinge feels solid under moderate load → progress.\n  → Full guide: https://gravelgodcycling.com/strength\n\nMasters, consistency beats intensity. Show up.",
    'Max Strength (A)': 'STRENGTH — Max Strength Phase\nSession A | Plan Week 5, Monday | RPE 6-8 | ~40 min\nProgressive overload. Real weight. Equipment: Barbell, DB, bench\n\n★ WARMUP (8 min) → All demos: gravelgodcycling.com/demos\n  • Downward Dog Lunge + Rotation ─ 5/side\n  • Goblet Squat Hold (light) ─ 30 sec\n  • Lateral Lunges ─ 8/side\n  • Arm Circles + Shoulder CARs ─ 10/side\n\n★ PREP (5 min) │ 2 rounds │ 45s rest\n  • MiniBand Lateral Walks ─ 10/side\n  • Monster Walk ─ 10 steps/direction\n  • Push-Up (slow, controlled) ─ 5 reps\n\n★ MAIN 1: Squat Pattern │ 4 sets │ 90s rest │ RPE 7-8\n  A1 Goblet Squat ─ 6-8 reps\n     → https://vimeo.com/111129796\n  A2 Push-Up + Shoulder Tap ─ 6-8 reps\n     → https://vimeo.com/111473395\n\n★ MAIN 2: Single-Leg Strength │ 4 sets │ 90s rest │ RPE 7-8\n  B1 Bulgarian Split Squat (or Goblet Squat) ─ 6-8 reps\n     → https://vimeo.com/111043982\n  B2 Floor Press or Incline DB Press ─ 10 reps\n     → Floor: https://www.youtube.com/watch?v=mKxS2JpUd_g\n     → Incline: https://www.youtube.com/watch?v=8iPEnn-ltC8\n\n★ CORE/CARRY (10 min) │ 3 rounds │ 60s rest\n  C1 Dead Bug (weighted) ─ 6-8 reps\n     → https://vimeo.com/111109110\n  C2 Suitcase Carry ─ 6-8 reps\n     → https://vimeo.com/111545001\n  C3 Hollow Body Hold ─ 20 sec\n     → https://www.youtube.com/watch?v=YaXPRqUwItQ\n\n★ COOLDOWN (5 min) → All demos: gravelgodcycling.com/demos\n  • Deep Squat Sit ─ 60 sec\n  • Hip Flexor Stretch ─ 45 sec/side\n  • Pigeon Pose ─ 45 sec/side\n\n★ ZERO EQUIPMENT (Hotel/Travel)\n  • Goblet Squat → Air Squat (add jump for challenge)\n  • Push-Up + Tap → Same\n  • BSS → Reverse Lunge (BW, alternate)\n  • Floor/Incline Press → Decline Push-Up (feet elevated)\n  • Carries → High-Knee March 40 sec/side\n\n★ NOTES\n  Hypertrophy zone: 8-12 reps, last 2 should be hard.\n  → BSS hurting your knee? Swap to Goblet Squat, same reps.\n  → KB jump too big? Add reps or 2-sec pause before adding weight.\n  → Unilateral failing? Go bilateral. Strength > wobble.\n  → Full guide: https://gravelgodcycling.com/strength\n\nMasters, consistency beats intensity. Show up.',
    'Max Strength (B)': "STRENGTH — Max Strength Phase\nSession B | Plan Week 5, Thursday | RPE 6-8 | ~40 min\nProgressive overload. Real weight. Equipment: Barbell, DB, bench\n\n★ WARMUP (8 min) → All demos: gravelgodcycling.com/demos\n  • Cat-Cow ─ 10 reps\n  • World's Greatest Stretch ─ 5/side\n  • Hip Circles (standing) ─ 10/side\n  • Band Pull-Aparts ─ 15 reps\n\n★ PREP (5 min) │ 2 rounds │ 45s rest\n  • Glute Bridge (banded) ─ 15 reps\n  • Dead Hang or Lat Stretch ─ 20 sec\n  • Good Morning (bodyweight) ─ 10 reps\n\n★ MAIN 1: Hinge Pattern │ 4 sets │ 90s rest │ RPE 7-8\n  A1 Single-Leg RDL (or Conventional RDL) ─ 6-8 reps\n     → https://vimeo.com/111545574\n  A2 Bent-Over DB Row ─ 6-8 reps\n     → https://vimeo.com/111048714\n\n★ MAIN 2: Pull + Hinge │ 4 sets │ 90s rest │ RPE 7-8\n  B1 KB/DB Deadlift ─ 6-8 reps\n     → https://vimeo.com/111040676\n  B2 Inverted Row or Pull-Up ─ 6-10 reps\n     → Inverted: https://www.youtube.com/watch?v=GdyhjXlxE-U\n     → Pull-Up: https://www.youtube.com/watch?v=eGo4IYlbE5g\n     → Default: Inverted Row. Pull-Up only if you own 5+ strict reps.\n\n★ CORE (10 min) │ 3 rounds │ 60s rest\n  C1 Pallof Press (hold 5 sec) ─ 6-8 reps\n     → https://vimeo.com/111469204\n  C2 Side Plank ─ 6-8 reps\n     → https://vimeo.com/111522888\n  C3 Band Chop ─ 6-8 reps\n     → https://vimeo.com/111132217\n\n★ COOLDOWN (5 min) → All demos: gravelgodcycling.com/demos\n  • 90-90 Hip Stretch ─ 45 sec/side\n  • Supine Hamstring Stretch ─ 45 sec/side\n  • Thread the Needle ─ 5/side\n\n★ ZERO EQUIPMENT (Hotel/Travel)\n  • Single-Leg RDL → Same (BW, reach to floor)\n  • Bent-Over DB Row → Superman Pull (face-down, lift arms/chest)\n  • KB/DB Deadlift → Good Morning (BW)\n  • Inverted Row/Pull-Up → Towel Row or under table\n  • Band Chop → Russian Twist (fast)\n\n★ NOTES\n  Hypertrophy zone: 8-12 reps builds muscle that serves the bike.\n  → SL RDL wobbling? Switch to Conventional RDL.\n  → No pull-up bar? Inverted row IS the exercise.\n  → KB jump too big? Add reps or pause before adding weight.\n  → Full guide: https://gravelgodcycling.com/strength\n\nMasters, consistency beats intensity. Show up.",
    'Power (A)': "STRENGTH — Power Phase\nSession A | Plan Week 11, Monday | RPE 5-7 | ~40 min\nPower you can actually use. Equipment: DB, KB, bands, bodyweight\n\n★ WARMUP (8 min) → All demos: gravelgodcycling.com/demos\n  • Jump Rope or Jumping Jacks ─ 60 sec\n  • Leg Swings (front/back + lateral) ─ 10/direction\n  • Goblet Squat (light, fast) ─ 5 reps\n  • Arm Circles + Clapping Push-Ups ─ 10 reps\n\n★ POWER PREP (5 min) │ 2 rounds │ 60s rest\n  • Box Jump (stick landing) ─ 3-5 reps (explosive)\n     → https://vimeo.com/111032509\n  • Med Ball Slam or Squat Jump ─ 6 reps\n     → Slam: https://www.youtube.com/watch?v=3r70rXMHt4k\n     → Squat Jump: https://www.youtube.com/watch?v=1u7S018Nt1M\n  • Broad Jump (step back) ─ 5 reps\n     → https://www.youtube.com/watch?v=7s8iH3mJzhk\n\n★ MAIN 1: Explosive Squat │ 4 sets │ 2 min rest │ Max Intent\n  A1 Jump Squat (bodyweight) ─ 3-5 reps (explosive)\n     → https://vimeo.com/111473749\n  A2 Plyo Push-Up (hands leave ground) ─ 3-5 reps (explosive)\n     → https://vimeo.com/111126228\n\n★ MAIN 2: Loaded Power │ 4 sets │ 2 min rest │ RPE 7\n  B1 Goblet Squat (moderate, FAST up) ─ 3-5 reps (explosive)\n     → https://vimeo.com/111129796\n  B2 Med Ball Chest Pass or Explosive Push-Up ─ 3-5 reps (explosive)\n     → https://vimeo.com/111126228\n\n★ CORE (8 min) │ 2 rounds │ 60s rest\n  C1 Med Ball Rotational Throw or Russian Twist ─ 6/side\n     → Throw: https://www.youtube.com/watch?v=YRiUvhz2lag\n     → Twist: https://www.youtube.com/watch?v=wkD8rjkodUI\n  C2 Plank + Shoulder Tap (fast) ─ 10/side\n  C3 Hollow Body Rock ─ 15 sec\n     → https://www.youtube.com/watch?v=mqnf9n0SPU0\n\n★ COOLDOWN (5 min) → All demos: gravelgodcycling.com/demos\n  • Deep Squat Sit ─ 60 sec\n  • Quad Stretch (standing) ─ 30 sec/side\n  • Hip Flexor Stretch ─ 45 sec/side\n\n★ ZERO EQUIPMENT (Hotel/Travel)\n  • Jump Squat → Same (BW)\n  • Plyo Push-Up → Same (or from knees)\n  • Goblet Squat → Air Squat Jump\n  • Med Ball Chest Pass → Explosive Push-Up or Shadow Box\n  • Med Ball Throw → Russian Twist (fast)\n\n★ NOTES\n  Power phase: Intent > load. Move fast, land soft.\n  Full rest = full power. Don't rush sets.\n  → Can't do plyo push-up? Fast regular push-up works.\n  → KB jump too big? Add reps or pause before adding weight.\n  → If tired, skip a set. Quality only.\n  → Full guide: https://gravelgodcycling.com/strength\n\nMasters, consistency beats intensity. Show up.",
    'Power (B)': 'STRENGTH — Power Phase\nSession B | Plan Week 11, Thursday | RPE 5-7 | ~40 min\nPower you can actually use. Equipment: DB, KB, bands, bodyweight\n\n★ WARMUP (8 min) → All demos: gravelgodcycling.com/demos\n  • Jump Rope ─ 60 sec\n  • Hip Circles (standing) ─ 10/side\n  • Hinge + Reach (no weight) ─ 10 reps\n  • Band Pull-Aparts ─ 15 reps\n\n★ POWER PREP (5 min) │ 2 rounds │ 60s rest\n  • KB Swing (light, focus on snap) ─ 10 reps\n     → https://www.youtube.com/watch?v=sSESeQAir2M\n  • Broad Jump (step back) ─ 5 reps\n     → https://www.youtube.com/watch?v=7s8iH3mJzhk\n  • Explosive Row or Jump Pull-Up ─ 3 reps\n\n★ MAIN 1: Ballistic Hinge │ 4 sets │ 2 min rest │ Max Intent\n  A1 KB Swing (2-hand) ─ 12 reps\n     → https://www.youtube.com/watch?v=sSESeQAir2M\n  A2 Explosive Inverted Row or Band Pull ─ 3-5 reps (explosive)\n     → https://vimeo.com/111033323\n     → Default: Fast inverted row, chest to bar\n     → No bar? Explosive band row\n\n★ MAIN 2: Power Hinge │ 4 sets │ 2 min rest │ RPE 7\n  B1 KB Swing to Goblet Catch (or heavy swing) ─ 3-5 reps (explosive)\n     → https://vimeo.com/111129801\n  B2 Explosive Pull-Up or Steep Inverted Row ─ 5-6 reps\n     → Pull-Up: https://www.youtube.com/watch?v=eGo4IYlbE5g\n     → Inverted: https://www.youtube.com/watch?v=GdyhjXlxE-U\n     → Pull-Up only if 5+ strict reps\n\n★ CORE (8 min) │ 2 rounds │ 60s rest\n  C1 Med Ball Rotational Throw or Russian Twist ─ 6/side\n     → Throw: https://www.youtube.com/watch?v=YRiUvhz2lag\n     → Twist: https://www.youtube.com/watch?v=wkD8rjkodUI\n  C2 Side Plank w/ Hip Drop ─ 3-5 reps (explosive)\n     → https://vimeo.com/111522888\n  C3 Pallof Press ─ 3-5 reps (explosive)\n     → https://vimeo.com/111469204\n\n★ COOLDOWN (5 min) → All demos: gravelgodcycling.com/demos\n  • 90-90 Hip Stretch ─ 45 sec/side\n  • Pigeon Pose ─ 45 sec/side\n  • Hamstring Stretch ─ 30 sec/side\n\n★ ZERO EQUIPMENT (Hotel/Travel)\n  • KB Swing → Broad Jump or Frog Jump (hip snap)\n  • Explosive Inverted Row → Explosive Towel Row or Superman Pull\n  • Explosive Pull-Up → Same substitute\n  • Med Ball Throw → Russian Twist (fast)\n\n★ NOTES\n  KB Swing = cycling power transfer. Snap the hips.\n  → No pull-up bar? Inverted row IS the exercise.\n  → KB jump too big? Add reps or pause before adding weight.\n  → If form breaks → lighter weight or more rest.\n  → Full guide: https://gravelgodcycling.com/strength\n\nMasters, consistency beats intensity. Show up.',
    'Maintenance (A)': "STRENGTH — Maintenance Phase\nSession A | Plan Week 15, Monday | RPE 5-6 | ~40 min\nMaintain. Don't detrain. Equipment: Bodyweight, bands, light DB\n\n★ WARMUP (5 min) → All demos: gravelgodcycling.com/demos\n  • Light Jog in Place ─ 60 sec\n  • Leg Swings ─ 8/direction\n  • Air Squat ─ 8 reps\n  • Arm Circles ─ 8/direction\n\n★ ACTIVATION (5 min) │ 1 round\n  • Box Jump or Squat Jump (light) ─ 8 reps\n     → https://vimeo.com/111032509\n  • Push-Up ─ 5 reps\n  • Lateral Lunge ─ 5/side\n\n★ MAIN (10 min) │ 2 sets │ 2 min rest │ Stay Sharp\n  A1 Goblet Squat (light) ─ 8 reps\n     → https://vimeo.com/111129796\n  A2 Push-Up ─ 8 reps\n     → https://vimeo.com/111473394\n  A3 Jump Squat ─ 8 reps\n     → https://vimeo.com/111473749\n\n★ CORE (5 min) │ 1-2 rounds\n  C1 Plank ─ 8 reps\n     → https://vimeo.com/111471004\n  C2 Dead Bug ─ 8 reps\n     → https://vimeo.com/111109110\n  C3 Ab Wheel or Weighted Dead Bug ─ 6 reps\n     → Ab Wheel: https://www.youtube.com/watch?v=rGevQLZ5aOw\n     → Weighted DB: https://www.youtube.com/watch?v=xmQ9zF3DoW8\n\n★ COOLDOWN (5 min) → All demos: gravelgodcycling.com/demos\n  • Stretch what's tight\n  • Focus on hip flexors + quads\n\n★ ZERO EQUIPMENT (Hotel/Travel)\n  • Goblet Squat → Air Squat\n  • Push-Up → Same\n  • Jump Squat → Same\n  • Ab Wheel → Plank Knee-to-Elbow\n\n★ NOTES\n  Minimal effective dose. Don't dig a hole.\n  Race week? Consider skipping or 1 set only.\n  You're sharp. Stay sharp. Trust the work.\n  → Full guide: https://gravelgodcycling.com/strength\n\nMasters, consistency beats intensity. Show up.",
}

TEMPLATE_KEYS: Dict[str, str] = {
    "foundation_a": "Foundation (A)",
    "foundation_b": "Foundation (B)",
    "max_strength_a": "Max Strength (A)",
    "max_strength_b": "Max Strength (B)",
    "power_a": "Power (A)",
    "power_b": "Power (B)",
    "maintenance_a": "Maintenance (A)",
}

# ---------------------------------------------------------------------------
# 2. Catalog reference data -- subset of outputs/rx_exercise_catalog.json
#    (690 exercises) actually referenced by EXACT_MAP/FUZZY_MAP below.
#    {catalog id: {title, videoUrl}}.
# ---------------------------------------------------------------------------
CATALOG: Dict[int, Dict[str, str]] = {
    144: {"title": "Goblet Squat", "videoUrl": "https://youtu.be/xQrRzGYsiyo"},
    786: {"title": "Shoulder Tap", "videoUrl": "https://youtu.be/mlgGw5t-Tz8"},
    422: {"title": "Banded Monster Walk", "videoUrl": "https://youtu.be/eVIX8dqtqTA"},
    579: {"title": "Glute Bridge", "videoUrl": "https://youtu.be/gR-RLIoLCDw"},
    7: {"title": "Band Pull Apart", "videoUrl": "https://youtu.be/2Tf_E4cYmD4"},
    145: {"title": "Good Morning", "videoUrl": "https://youtu.be/49rgzdBWWj4"},
    151: {"title": "Single Arm DB Row", "videoUrl": "https://youtu.be/efcUQe-Hhi8"},
    81: {"title": "Single Leg Glute Bridge", "videoUrl": "https://youtu.be/ZUtrQ8EU5t0"},
    358: {"title": "Pallof Press", "videoUrl": "https://www.youtube.com/watch?v=f_D0GByfZh0"},
    79: {"title": "Side Plank", "videoUrl": "https://youtu.be/rrrxDvyfYN0"},
    256: {"title": "Bird Dog", "videoUrl": "https://www.youtube.com/watch?v=-LRjkbEy-qU"},
    29: {"title": "Close Grip Push Up", "videoUrl": "https://youtu.be/W_jcsoo-mKM"},
    24: {"title": "Barbell Bulgarian Split Squat", "videoUrl": "https://youtu.be/s_xmy9gt37U"},
    569: {"title": "Floor Press", "videoUrl": "https://youtu.be/qakAJIXeV1Y"},
    516: {"title": "DB Row", "videoUrl": "https://youtu.be/VZXUUnQP_5Q"},
    32: {"title": "DB Deadlift", "videoUrl": "https://youtu.be/zjyvtMvVrUc"},
    617: {"title": "Inverted Row", "videoUrl": "https://youtu.be/bpEndSF0L70"},
    21: {"title": "Box Jump", "videoUrl": "https://youtu.be/8tO-FC0l720"},
    23: {"title": "Broad Jump", "videoUrl": "https://youtu.be/QbQVZdJ7XfI"},
    508: {"title": "DB Jump Squat", "videoUrl": "https://youtu.be/yaQzkLorww4"},
    718: {"title": "Plyo Push Up", "videoUrl": "https://youtu.be/biWXRJ4vo9U"},
    598: {"title": "High Plank Shoulder Tap", "videoUrl": "https://youtu.be/5pdWy6pY2uo"},
    77: {"title": "Russian KB swing", "videoUrl": "https://youtu.be/PvdVVJ--DH8"},
    73: {"title": "Pull Up", "videoUrl": "https://youtu.be/d3IlZYzLeaI"},
    71: {"title": "Plank", "videoUrl": "https://youtu.be/l8EaE5zMENQ"},
    63: {"title": "Body Weight Lateral Lunge", "videoUrl": "https://youtu.be/WFJjREH6AsU"},
}

# ---------------------------------------------------------------------------
# 3. MAPPING TABLES (reviewable) -- Matti-approved "nearest equivalent + notes"
#    policy. Keys are the *primary* movement text as the parser derives it
#    (after stripping a top-level " OR "/" or " alternative; a parenthetical
#    "(or X)" is NOT a top-level split -- see _split_top_level_or).
#
#    EXACT_MAP is keyed by the movement's *core* text (parenthetical cues
#    stripped) -- these are movements whose catalog title is (up to
#    punctuation) the same as the template's movement name.
#
#    FUZZY_MAP is keyed by the *full* primary text (cues included) -- these
#    are movements with no exact catalog title; the chosen id is the closest
#    semantic candidate from outputs/strength_catalog_map.json's candidate
#    lists, picked by hand per movement (see inline comments for judgment
#    calls with more than one candidate).
# ---------------------------------------------------------------------------
EXACT_MAP: Dict[str, int] = {
    "Goblet Squat": 144,
    "Glute Bridge": 579,
    "Band Pull-Apart": 7,
    "Good Morning": 145,
    "Single-Arm DB Row": 151,
    "Single-Leg Glute Bridge": 81,
    "Pallof Press": 358,
    "Bird Dog": 256,
    "Floor Press": 569,
    "Inverted Row": 617,
    "Box Jump": 21,
    "Broad Jump": 23,
    "Plyo Push-Up": 718,
    "Side Plank": 79,
    "Plank": 71,
}

FUZZY_MAP: Dict[str, int] = {
    "Monster Walk": 422,  # candidate: Banded Monster Walk (only candidate offered)
    "Push-Up + Shoulder Tap": 786,  # candidate: Shoulder Tap (only candidate offered)
    # No plain "Push Up" in the 690-exercise catalog (confirmed: bare
    # "Push-Up" fuzzy-matched to the same 3 push-up-variant candidates in
    # every template it appears in). Close Grip Push Up is the least
    # biomechanically-altered stand-in of {Close Grip, Diamond, Feet
    # Elevated} for a plain push-up; used consistently everywhere "Push-Up"
    # appears bare or with a tempo/cue qualifier.
    "Push-Up (slow, controlled)": 29,
    "Push-Up": 29,
    "Bulgarian Split Squat (or Goblet Squat)": 24,  # equipment list includes Barbell; literal name match
    "Bent-Over DB Row": 516,  # candidates: Single Arm Bent Over DB Row, DB Row -> DB Row (not single-arm in source)
    "KB/DB Deadlift": 32,  # candidates: DB Deadlift, Deadlift -> DB Deadlift (matches "DB" in source name)
    "Jump Squat (bodyweight)": 508,  # Matti example: Jump Squat (bodyweight) -> DB Jump Squat
    "Jump Squat": 508,
    "KB Swing (light, focus on snap)": 77,  # candidates: Russian/American/Change-Hands KB swing -> Russian (2-hand default)
    "KB Swing (2-hand)": 77,  # Matti example: KB Swing (2-hand) -> Russian KB swing
    "Explosive Inverted Row": 617,  # candidate: Inverted Row (only candidate offered)
    "Explosive Pull-Up": 73,  # candidate: Pull Up (only candidate offered)
    "Side Plank w/ Hip Dip": 79,  # candidates: Plank, Side Plank -> Side Plank (closer semantic)
    "Side Plank w/ Hip Drop": 79,  # same choice, consistent with the Hip Dip variant above
    "Plank + Shoulder Tap (fast)": 598,  # candidates: Plank, High Plank Shoulder Tap, Shoulder Tap -> compound match
    "Lateral Lunge": 63,  # candidates: Body Weight/TRX/DB Lateral Lunge -> bodyweight (template equipment: bodyweight/bands/light DB)
}

# Missing-from-catalog movements -> canonical custom-exercise title. Variant
# spellings of the same movement (e.g. "Dead Bug" / "Dead Bug (weighted)")
# collapse to one canonical custom exercise; the load/variant cue rides in
# the prescription's coachNotes instead of a duplicate custom exercise.
CUSTOM_CANONICAL: Dict[str, str] = {
    "Hip Rails": "Hip Rails",
    "MiniBand Marches": "MiniBand Marches",
    "Dead Bug (add light weight)": "Dead Bug",
    "Dead Bug (weighted)": "Dead Bug",
    "Dead Bug": "Dead Bug",
    "Suitcase Carry (single side)": "Suitcase Carry",
    "Suitcase Carry": "Suitcase Carry",
    "MiniBand Lateral Walks": "MiniBand Lateral Walks",
    "Hollow Body Hold": "Hollow Body Hold",
    "KB/DB RDL (moderate load)": "KB/DB RDL",
    "Dead Hang": "Dead Hang",
    "Single-Leg RDL (or Conventional RDL)": "Single-Leg RDL",
    "Band Chop": "Band Chop",
    "Med Ball Slam": "Med Ball Slam",
    "Med Ball Chest Pass": "Med Ball Chest Pass",
    "Med Ball Rotational Throw": "Med Ball Rotational Throw",
    "Hollow Body Rock": "Hollow Body Rock",
    "Explosive Row": "Explosive Row",
    "KB Swing to Goblet Catch (or heavy swing)": "KB Swing to Goblet Catch",
    "Ab Wheel": "Ab Wheel",
}

# Prescription parameter catalog stub. Reps is captured verbatim in
# plan_day_capture_netlog.json / structured_strength_PUT_payload.json. Time
# is NOT captured anywhere in the provided references -- this shape is a
# best-effort inference mirroring Reps' structure and is flagged as an
# assumption pending a live capture.
PARAM_DEFS: Dict[str, Dict[str, object]] = {
    "Reps": {"title": "Reps", "unit": {"title": "Reps", "abbreviation": "", "unit": "Reps"}, "category": "Reps"},
    "Time": {"title": "Time", "unit": {"title": "Seconds", "abbreviation": "sec", "unit": "Seconds"}, "category": "Time"},
}

_BLOCK_TYPE_ONLY_NAMES = ("PREP", "CORE", "CORE/CARRY", "FINISHER")
_WARMUP_ONLY_NAMES = ("ACTIVATION", "POWER PREP")
_BLOCK_NAMES = (
    "ZERO EQUIPMENT",
    "POWER PREP",
    "CORE/CARRY",
    "WARMUP",
    "COOLDOWN",
    "ACTIVATION",
    "FINISHER",
    "NOTES",
    "PREP",
    "CORE",
    "MAIN",
)

_URL_RE = re.compile(r"https?://\S+")
_DURATION_RE = re.compile(r"~(\d+)\s*min")
_TIME_RE = re.compile(r"^(\d+)(?:-\d+)?\s*(sec|min)\b", re.IGNORECASE)
_NUM_RE = re.compile(r"^(\d+)")
_SETS_ROUNDS_RE = re.compile(r"^(\d+)(?:-(\d+))?\s*(sets?|rounds?)\b", re.IGNORECASE)
_RPE_RE = re.compile(r"^RPE\s*([\d\-]+)$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 4. Raw-text parsing structures
# ---------------------------------------------------------------------------
@dataclass
class _RawMovement:
    slot: Optional[str]
    raw_name: str
    presc_text: Optional[str]
    details: List[str] = field(default_factory=list)


@dataclass
class _RawBlock:
    name: str
    num: Optional[int]
    subtitle: Optional[str]
    duration: Optional[str]
    meta: List[str]
    movements: List[_RawMovement] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)


def _parse_header(line: str) -> Tuple[str, Optional[int], Optional[str], Optional[str], List[str]]:
    body = line[1:].strip() if line.startswith("★") else line.strip()
    name = None
    for cand in _BLOCK_NAMES:
        if body == cand or body.startswith(cand + " ") or body.startswith(cand + ":") or body.startswith(cand + "("):
            name = cand
            body = body[len(cand):].strip()
            break
    if name is None:
        raise ValueError(f"Unrecognized block header: {line!r}")

    num = None
    m = _NUM_RE.match(body)
    if m and not body.startswith("("):
        num = int(m.group(1))
        body = body[m.end():].strip()

    subtitle = None
    if body.startswith(":"):
        body = body[1:].strip()
        m = re.match(r"^([^(│]+)", body)
        if m:
            subtitle = m.group(1).strip()
            body = body[m.end():].strip()

    duration = None
    m = re.match(r"^\(([^)]*)\)\s*", body)
    if m:
        duration = m.group(1)
        body = body[m.end():].strip()

    meta: List[str] = []
    if body.startswith("│"):
        meta = [seg.strip() for seg in body.split("│") if seg.strip()]

    return name, num, subtitle, duration, meta


def _parse_template_raw(text: str) -> Tuple[List[str], List[_RawBlock]]:
    lines = text.split("\n")
    preamble: List[str] = []
    blocks: List[_RawBlock] = []
    current: Optional[_RawBlock] = None
    seen_header = False

    for line in lines:
        if line.startswith("★"):
            name, num, subtitle, duration, meta = _parse_header(line)
            current = _RawBlock(name=name, num=num, subtitle=subtitle, duration=duration, meta=meta)
            blocks.append(current)
            seen_header = True
            continue

        if not seen_header:
            preamble.append(line)
            continue

        assert current is not None
        if current.name in ("ZERO EQUIPMENT", "NOTES"):
            current.raw_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("→"):  # -> detail line for the previous movement
            detail = stripped[1:].strip()
            if current.movements:
                current.movements[-1].details.append(detail)
            continue

        m_slot = re.match(r"^([A-C]\d)\s+(.*)$", stripped)
        m_bullet = re.match(r"^•\s*(.*)$", stripped)
        if m_slot:
            slot, rest = m_slot.group(1), m_slot.group(2)
        elif m_bullet:
            slot, rest = None, m_bullet.group(1)
        else:
            slot, rest = None, stripped

        if " ─ " in rest:
            name_part, presc_part = rest.split(" ─ ", 1)
        else:
            name_part, presc_part = rest, None

        current.movements.append(
            _RawMovement(
                slot=slot,
                raw_name=name_part.strip(),
                presc_text=(presc_part.strip() if presc_part else None),
            )
        )

    return preamble, blocks


# ---------------------------------------------------------------------------
# 5. Movement text helpers (OR-splitting, cue extraction, catalog resolution)
# ---------------------------------------------------------------------------
def _split_top_level_or(text: str) -> Tuple[str, Optional[str]]:
    """Split on a top-level ' OR '/' or ' separator (outside parentheses).

    A parenthetical "(or X)" is NOT a top-level alternative -- it stays part
    of the primary text and is later surfaced as a coachNotes cue.
    """
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0:
            m = re.match(r"\s+(?:OR|or)\s+", text[i:])
            if m:
                return text[:i].strip(), text[i + len(m.group(0)):].strip()
        i += 1
    return text, None


def _split_cues(text: str) -> Tuple[str, List[str]]:
    core = re.sub(r"\s*\([^)]*\)", "", text).strip()
    cues = re.findall(r"\(([^)]*)\)", text)
    return core, cues


def _resolve_exercise(primary_name: str) -> Tuple[str, Dict[str, str], str]:
    """Returns (match_kind, exercise_ref, canonical_title).

    match_kind in {'exact', 'fuzzy', 'custom'}. exercise_ref is either a
    catalog stub {id, title, videoUrl} or a {custom: title} placeholder.
    """
    core, _cues = _split_cues(primary_name)
    if core in EXACT_MAP:
        cid = EXACT_MAP[core]
        c = CATALOG[cid]
        return "exact", {"id": str(cid), "title": c["title"], "videoUrl": c["videoUrl"]}, c["title"]
    if primary_name in FUZZY_MAP:
        cid = FUZZY_MAP[primary_name]
        c = CATALOG[cid]
        return "fuzzy", {"id": str(cid), "title": c["title"], "videoUrl": c["videoUrl"]}, c["title"]
    if primary_name in CUSTOM_CANONICAL:
        canonical = CUSTOM_CANONICAL[primary_name]
        return "custom", {"custom": canonical}, canonical
    raise ValueError(
        f"No catalog mapping for movement {primary_name!r} -- add it to "
        "EXACT_MAP, FUZZY_MAP, or CUSTOM_CANONICAL."
    )


def _movement_prescription(raw_name: str, presc_text: Optional[str]):
    primary_name, alt_name = _split_top_level_or(raw_name)
    primary_presc, alt_presc = (presc_text, None)
    if presc_text:
        primary_presc, alt_presc = _split_top_level_or(presc_text)
    return primary_name, alt_name, primary_presc, alt_presc


def _parse_param(presc_text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not presc_text:
        return None, None
    presc_text = presc_text.strip()
    m = _TIME_RE.match(presc_text)
    if m:
        low, unit = int(m.group(1)), m.group(2).lower()
        seconds = low * 60 if unit == "min" else low
        return "Time", str(seconds)
    m = _NUM_RE.match(presc_text)
    if m:
        return "Reps", m.group(1)
    return None, None


def _movement_notes(
    primary_name: str,
    presc_text: Optional[str],
    match_kind: str,
    canonical_title: str,
    alt_text: Optional[str],
) -> Optional[str]:
    frags: List[str] = []
    if match_kind == "fuzzy":
        if primary_name != canonical_title:
            frags.append(f"Orig: {primary_name}")
    elif match_kind == "exact":
        _core, cues = _split_cues(primary_name)
        if cues:
            frags.append(f"Cue: {', '.join(cues)}")
    elif match_kind == "custom":
        extra = primary_name.replace(canonical_title, "", 1).strip()
        if extra.startswith("(") and extra.endswith(")"):
            inner = extra[1:-1].strip()
        else:
            inner = extra
        m_or = re.match(r"^or\s+(.+)$", inner, re.IGNORECASE)
        if m_or:
            frags.append(f"or {m_or.group(1)}")
        elif inner:
            frags.append(f"Cue: {inner}")

    if presc_text and re.search(r"-\d+|/|\(", presc_text):
        frags.append(f"Rx: {presc_text}")
    if alt_text:
        frags.append(f"or {alt_text}")

    return " · ".join(frags) if frags else None


def _select_primary_url(details: List[str], primary_name: str, alt_name: Optional[str]) -> Optional[str]:
    fallback = None
    for d in details:
        m = _URL_RE.search(d)
        if not m:
            continue
        url = m.group(0)
        if fallback is None:
            fallback = url
        if ":" in d:
            label = d.split(":", 1)[0].strip().lower()
            if label and label in primary_name.lower():
                return url
    return fallback


# ---------------------------------------------------------------------------
# 6. Block-type mapping + assembly
# ---------------------------------------------------------------------------
def _block_type_and_kind(block: _RawBlock) -> Tuple[str, str]:
    if block.name == "WARMUP":
        return "WarmUp", "coach_only"
    if block.name == "COOLDOWN":
        return "CoolDown", "coach_only"
    if block.name in _BLOCK_TYPE_ONLY_NAMES:
        return "Circuit", "prescriptions"
    if block.name in _WARMUP_ONLY_NAMES:
        return "WarmUp", "prescriptions"
    if block.name == "MAIN":
        return ("Superset" if len(block.movements) >= 2 else "SingleExercise"), "prescriptions"
    raise ValueError(f"Unmapped block name: {block.name}")


def _sets_count(block: _RawBlock) -> Tuple[int, bool]:
    for seg in block.meta:
        m = _SETS_ROUNDS_RE.match(seg)
        if m:
            return int(m.group(1)), m.group(2) is not None
    return 1, False


def _block_coach_notes(block: _RawBlock, sets_is_range: bool) -> Optional[str]:
    frags: List[str] = []
    rpe = None
    rest = None
    others: List[str] = []
    for seg in block.meta:
        if _SETS_ROUNDS_RE.match(seg):
            if sets_is_range:
                others.append(seg)
            continue
        m_rpe = _RPE_RE.match(seg)
        if m_rpe:
            rpe = f"RPE {m_rpe.group(1)}"
            continue
        if re.search(r"\brest\b", seg, re.IGNORECASE):
            rest = f"{seg} between sets"
            continue
        others.append(seg)
    if rpe:
        frags.append(rpe)
    if rest:
        frags.append(rest)
    frags.extend(others)
    return " · ".join(frags) if frags else None


def _make_sets(uuid_factory: Callable[[], str], param_type: str, value: str, count: int) -> List[Dict[str, object]]:
    sets = []
    for _ in range(count):
        sets.append(
            {
                "id": uuid_factory(),
                "isComplete": False,
                "parameterValues": [
                    {
                        "id": uuid_factory(),
                        "parameter": param_type,
                        "executedValue": None,
                        "inputFormat": "Integer",
                        "prescribedValue": value,
                    }
                ],
            }
        )
    return sets


def _make_prescription(
    uuid_factory: Callable[[], str],
    exercise_ref: Dict[str, str],
    param_type: str,
    value: str,
    count: int,
    coach_notes: Optional[str],
) -> Dict[str, object]:
    pdef = PARAM_DEFS[param_type]
    summary = "{Reps} reps" if param_type == "Reps" else "{Time} sec"
    return {
        "id": uuid_factory(),
        "exercise": exercise_ref,
        "parameters": [
            {
                "parameter": param_type,
                "title": pdef["title"],
                "unit": pdef["unit"],
                "category": pdef["category"],
                "id": uuid_factory(),
            }
        ],
        "coachNotes": coach_notes,
        "setSummaryTemplate": summary,
        "sets": _make_sets(uuid_factory, param_type, value, count),
    }


def _build_block(block: _RawBlock, uuid_factory: Callable[[], str]) -> Tuple[Dict[str, object], int, int]:
    block_type, kind = _block_type_and_kind(block)
    block_title = block_type

    if kind == "coach_only":
        lines = []
        for mv in block.movements:
            line = f"• {mv.raw_name}"
            if mv.presc_text:
                line += f" ─ {mv.presc_text}"
            lines.append(line)
        lines.append("(demos: gravelgodcycling.com/demos)")
        block_dict = {
            "prescriptions": [],
            "blockType": block_type,
            "title": block_title,
            "coachNotes": "\n".join(lines),
            "parameters": [],
            "isComplete": False,
            "compliancePercent": 0,
            "complianceState": "NoCompletion",
            "id": uuid_factory(),
        }
        return block_dict, 0, 0

    count, is_range = _sets_count(block)
    block_coach_notes = _block_coach_notes(block, is_range)
    prescriptions = []
    total_sets = 0
    last_title = None
    for mv in block.movements:
        primary_name, alt_name, primary_presc, alt_presc = _movement_prescription(mv.raw_name, mv.presc_text)
        param_type, value = _parse_param(primary_presc)
        if param_type is None:
            raise ValueError(f"Could not parse prescription text {mv.presc_text!r} for {mv.raw_name!r}")
        match_kind, exercise_ref, canonical_title = _resolve_exercise(primary_name)
        alt_text = None
        if alt_name:
            alt_text = f"{alt_name} ({alt_presc})" if alt_presc else alt_name
        coach_notes = _movement_notes(primary_name, primary_presc, match_kind, canonical_title, alt_text)
        # Free-text detail lines that aren't a demo link (e.g. "Default:
        # Inverted Row. Pull-Up only if you own 5+ strict reps.") carry real
        # coaching guidance -- fold them in rather than silently drop them.
        non_url_notes = [d for d in mv.details if not _URL_RE.search(d)]
        if non_url_notes:
            extra = " · ".join(f"Note: {d}" for d in non_url_notes)
            coach_notes = f"{coach_notes} · {extra}" if coach_notes else extra
        prescriptions.append(_make_prescription(uuid_factory, exercise_ref, param_type, value, count, coach_notes))
        total_sets += count
        last_title = canonical_title

    if block_type == "SingleExercise" and last_title:
        block_title = last_title

    block_dict = {
        "prescriptions": prescriptions,
        "blockType": block_type,
        "title": block_title,
        "coachNotes": block_coach_notes,
        "parameters": [],
        "isComplete": False,
        "compliancePercent": 0,
        "complianceState": "NoCompletion",
        "id": uuid_factory(),
    }
    return block_dict, len(prescriptions), total_sets


def _build_instructions(preamble: List[str], zero_block: Optional[_RawBlock], notes_block: Optional[_RawBlock]) -> str:
    parts = []
    pre_text = "\n".join(l for l in preamble if l.strip())
    if pre_text:
        parts.append(pre_text)
    if zero_block is not None:
        header = "ZERO EQUIPMENT" + (f" ({zero_block.duration})" if zero_block.duration else "")
        body = "\n".join(l.rstrip() for l in zero_block.raw_lines).strip("\n")
        parts.append(header + ("\n" + body if body else ""))
    if notes_block is not None:
        body = "\n".join(l.rstrip() for l in notes_block.raw_lines).strip("\n")
        parts.append("NOTES" + ("\n" + body if body else ""))
    text = "\n\n".join(parts)
    # Defensive: strip any non-gravelgodcycling.com link (none of the 7
    # templates actually contain one here; this guards future template edits).
    text = re.sub(r"https?://(?!gravelgodcycling\.com)\S+", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def _parse_duration_seconds(preamble: List[str]) -> int:
    for line in preamble:
        m = _DURATION_RE.search(line)
        if m:
            return int(m.group(1)) * 60
    return 2400


def _format_date(value) -> str:
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat().split("T")[0]
    raise TypeError(f"Unsupported prescribed_date type: {type(value)!r}")


# ---------------------------------------------------------------------------
# 7. Public API
# ---------------------------------------------------------------------------
def build_strength_doc(
    template_key: str,
    *,
    calendar_id,
    prescribed_date,
    doc_id: str,
    uuid_factory: Callable[[], str],
) -> Dict[str, object]:
    """Build a complete StructuredStrength PUT-request-body document.

    `template_key` is one of TEMPLATE_KEYS' keys (foundation_a, foundation_b,
    max_strength_a, max_strength_b, power_a, power_b, maintenance_a).
    `uuid_factory` is called with no args and must return a fresh id string
    for every block/prescription/parameter/set/parameterValue -- inject a
    deterministic (seeded) factory for reproducible tests.
    """
    display_key = TEMPLATE_KEYS.get(template_key)
    if display_key is None:
        raise ValueError(f"Unknown template_key {template_key!r}; expected one of {sorted(TEMPLATE_KEYS)}")

    preamble, raw_blocks = _parse_template_raw(SESSION_TEMPLATES[display_key])

    blocks_out: List[Dict[str, object]] = []
    total_prescriptions = 0
    total_sets = 0
    zero_block = None
    notes_block = None

    for rb in raw_blocks:
        if rb.name == "ZERO EQUIPMENT":
            zero_block = rb
            continue
        if rb.name == "NOTES":
            notes_block = rb
            continue
        block_dict, n_presc, n_sets = _build_block(rb, uuid_factory)
        blocks_out.append(block_dict)
        total_prescriptions += n_presc
        total_sets += n_sets

    return {
        "workoutType": "StructuredStrength",
        "lastUpdatedAt": None,
        "compliancePercent": None,
        "complianceState": "Unplanned",
        "structureCompliancePercent": None,
        "durationCompliancePercent": None,
        "tssCompliancePercent": None,
        "rpe": None,
        "feel": None,
        "blocks": blocks_out,
        "files": [],
        "snapshot": {
            "totalBlocks": len(blocks_out),
            "completedBlocks": 0,
            "totalSets": total_sets,
            "completedSets": 0,
            "totalPrescriptions": total_prescriptions,
            "completedPrescriptions": 0,
        },
        "prescribedDate": _format_date(prescribed_date),
        "prescribedStartTime": None,
        "startDateTime": None,
        "completedDateTime": None,
        "calendarId": calendar_id,
        "title": display_key,
        "instructions": _build_instructions(preamble, zero_block, notes_block),
        "prescribedDurationInSeconds": _parse_duration_seconds(preamble),
        "orderOnDay": None,
        "executedDurationInSeconds": None,
        "isLocked": False,
        "isHidden": False,
        "workoutSubTypeId": None,
        "prescribedTss": None,
        "prescribedIntensityFactor": None,
        "completedTss": None,
        "completedTssSource": None,
        "completedIntensityFactor": None,
        "id": doc_id,
    }


def _iter_all_custom_movements():
    for display_key in TEMPLATE_KEYS.values():
        _preamble, raw_blocks = _parse_template_raw(SESSION_TEMPLATES[display_key])
        for rb in raw_blocks:
            if rb.name in ("ZERO EQUIPMENT", "NOTES", "WARMUP", "COOLDOWN"):
                continue
            for mv in rb.movements:
                primary_name, alt_name, _primary_presc, _alt_presc = _movement_prescription(mv.raw_name, mv.presc_text)
                match_kind, _exercise_ref, canonical = _resolve_exercise(primary_name)
                if match_kind == "custom":
                    yield canonical, primary_name, mv.details, alt_name


def custom_exercises_needed() -> List[Dict[str, object]]:
    """The pre-pass manifest of custom exercises the CLI must create once,
    across all 7 templates, before any strength doc referencing them can be
    fully resolved (their prescriptions carry a {custom: title} placeholder
    until then).

    Returns a list of {title, videoUrl, movements_covered} sorted by title.
    """
    grouped: Dict[str, Dict[str, object]] = {}
    for canonical, primary_name, details, alt_name in _iter_all_custom_movements():
        entry = grouped.setdefault(canonical, {"title": canonical, "videoUrl": None, "movements_covered": []})
        if primary_name not in entry["movements_covered"]:
            entry["movements_covered"].append(primary_name)
        if entry["videoUrl"] is None:
            url = _select_primary_url(details, primary_name, alt_name)
            if url:
                entry["videoUrl"] = url
    return [grouped[k] for k in sorted(grouped)]
