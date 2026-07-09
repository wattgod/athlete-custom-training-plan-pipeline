# AGENTS.md — entry point for any coding agent

Binding instructions live in `CLAUDE.md` — read it first; it is written for
all agents, not just Claude. This repo is a production order pipeline:
customer money flows through it, so failure paths matter as much as
happy paths.

## Handover skills

Distilled operating knowledge — incidents, settled decisions, playbooks not
derivable from the code. Read the one matching your task before starting.

| Before you… | Read |
|---|---|
| Touch intake validation, checkout, delivery, failure paths | `.claude/skills/order-safety/SKILL.md` |
| Touch archetypes, race mapping, or the plan catalog | `.claude/skills/archetype-and-catalog/SKILL.md` |
| Touch workout/plan generation, scheduling, compliance | `.claude/skills/generator-conventions/SKILL.md` |

## Non-negotiables (full text in CLAUDE.md and the skills)

- Never hard-fail an order on a field the pipeline can estimate or defer.
- Failures are invisible to the customer, loud to the coach.
- Mark idempotency BEFORE long operations.
- Archetype IDs are a public contract — live race pages link to them.
