# AI writing on Matti Rowe's behalf

This policy applies to copy that will be sent, published, or displayed as Matti
Rowe, Gravel God, Roadie Labs, XC Ski Labs, or Matti's coaching/consulting
practice. It does not require ordinary code comments or internal engineering
notes to imitate Matti.

The canonical cross-brand profile is
`wattgod/writing-graph/self/voice-and-beliefs-profile.md`. The target repo's
brand, safety, and audience rules still apply. Current direct instruction from
Matti outranks both.

## Ground the voice before drafting

1. Name the surface, audience, stakes, topic, and register.
2. Read the canonical profile and the target repo's relevant voice guidance.
3. Retrieve one to three relevant, verified raw pieces from the writing graph.
   When the graph is cloned locally, use:

   ```bash
   python3 scripts/retrieve_voice.py "<topic, audience, or situation>"
   ```

4. Read the returned source pieces. Pull only the exact words, phrases,
   distinctions, or sentence rhythms that fit the new context.
5. Record source paths in working notes or the PR description. These provenance
   notes are not part of the published copy.
6. Draft from the actual judgment and facts. Retrieved language is evidence, not
   a quota.
7. Run the target repo's slop/voice gate. If none exists, run the writing graph's
   `scripts/check_ai_writing.py --strict` against the draft.
8. Apply the complete pinned `petergyang/no-ai-slop` edit workflow and every
   check in its `eval.md`. The deterministic gate is not a substitute for this
   editorial pass.

## Required no-ai-slop pass

The canonical copy is vendored in `wattgod/writing-graph/vendor/no-ai-slop/`
from https://github.com/petergyang/no-ai-slop at commit
`d30eddb9e04562234f2070b5ee63ca4649d9a05e`. Read both `SKILL.md` and
`eval.md`. Preserve the point, facts, vocabulary, useful edge, and natural
cadence while removing portable filler, fake drama, inflated claims, structural
tics, and formatting decoration.

Use detect mode for raw Matti-authored sources and derived analytical notes.
Name findings without scoring authorship or silently rewriting the evidence.
Historical use of a flagged pattern does not authorize an AI to imitate it.

Use edit mode for AI-assisted copy presented as Matti or one of his brands.
Make the minimum effective edit, run the strict mechanical gate, complete the
full human eval, and fix every failed check before approval. Portability,
meaning preservation, synonym cycling, robotic rhythm, and voice flattening
always require editorial judgment.

## Valid voice evidence

Prefer, in order:

1. Matti's current instruction or correction for this exact draft.
2. Matti's manually authored correspondence for the same person and surface.
3. The canonical profile plus one or two relevant voice/theme notes.
4. One to three verified raw pieces in the writing graph.
5. A verified-authored Google Doc approved for this audience and privacy level.

Never use generated copy, an AI summary, a transcript of someone else, copied
research, a template, an unverified Drive document, or mere file ownership as
Matti voice evidence. Do not expose private notes, athlete/client information,
employer material, or personal correspondence to make public copy feel
specific.

## Hard failures

- Invented quotes, anecdotes, beliefs, credentials, results, testimonials,
  client stories, or inside jokes.
- Corporate uplift or generic AI marketing: “unlock your potential,”
  “game-changing,” “next-level,” “world-class experience,” “elevate,”
  “supercharge,” “in today's fast-paced world,” “delve into,” “deep dive,”
  “look no further,” “we've got you covered,” or equivalent filler.
- Motivational wallpaper: “you've got this,” “trust the process,” “crush it,”
  “consistency is key,” “happy training,” or reassurance the reader did not ask
  for.
- Performing Matti with manufactured profanity, aggression, fragments, all
  caps, dark humor, gotchas, or stacked punchlines.
- Reusing a signature line because it sounds on-brand rather than because its
  original meaning fits.
- Uniformly clipped prose, uniformly polished prose, empty three-part cadences,
  fake intimacy, false scarcity, unsupported outcomes, or technical language
  used only to display expertise.
- Copy that could belong to any coach, consultant, or endurance brand after a
  noun swap.

## Final adversarial read

Before approval, identify:

- the real judgment and whether it appears early enough;
- the concrete detail that proves this is for this reader and purpose;
- the retrieved source language and why its original context fits;
- any line trying harder to sound like Matti than to help;
- any joke, metaphor, adjective, or paragraph removable without losing meaning;
- any certainty, concern, or promise not earned by the sources.

Voice is the consequence of judgment, evidence, and relationship. It is not a
bag of tricks.
