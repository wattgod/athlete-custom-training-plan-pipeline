# Road Racing Format + Category Progression

Status: implementation companion to ROAD_ADAPTATION_SPEC.md
Rules checked: 2026-07-16

## Outcome

A Roadie Labs intake can explicitly identify a criterium, road race, hill climb,
time trial, stage race, or fondo. That format reaches the athlete profile,
workout selector, guide, and coach-review artifacts. A missing format never
blocks an order: conservative race-name inference is allowed, otherwise the
plan remains generic road and is flagged for review.

The athlete's actual USA Cycling road category is collected independently of
estimated W/kg. License category controls the progression/strategy chapter; it
does not set training zones and it is not inferred from physiology.

## Acceptance criteria

1. Explicit format wins over race-name inference; unknown stays generic.
2. The protected VO2 workout remains present while a secondary workout and,
   where appropriate, long ride become format-aware.
3. Road category is optional, normalized, and never an order blocker.
4. The Roadie guide includes format strategy and the athlete's next-category
   development path, with current-rule links and no upgrade guarantee.
5. A Roadie form submission produces a package that can be built on the
   TrainingPeaks athlete named Example Athlete without purchasing the order.
6. Regression tests prove Gravel God behavior is unchanged when no event format
   is supplied.

## Product boundaries

- This is format-aware coaching, not a promise that every workout is a perfect
  course simulation.
- USA Cycling upgrade thresholds are dated reference material. The linked
  governing-body policy must be checked before calendar decisions.
- Training can improve performance, racecraft, and consistency. Results,
  finishes, points, approval, safety, and race availability remain external.
- No automatic TrainingPeaks fulfillment or cross-repository Worker is added.

## Evidence base

- [USA Cycling Policy VIII](https://usacycling.org/about-us/governance/policy-viii)
- [USA Cycling 2026 road upgrade chart](https://assets.usacycling.org/prod/documents/050726_Road.png)
- [Professional road-race power demands](https://pubmed.ncbi.nlm.nih.gov/19124890/)
- [Final sprint impairment after stochastic cycling](https://pmc.ncbi.nlm.nih.gov/articles/PMC6383108/)
- [Repeated sprinting in elite cyclists](https://pubmed.ncbi.nlm.nih.gov/34122152/)
- [Block periodization in trained cyclists](https://pubmed.ncbi.nlm.nih.gov/22646668/)
- [Aerobic interval format comparison](https://pubmed.ncbi.nlm.nih.gov/21812820/)
- [Uphill time-trial physiological profile](https://pubmed.ncbi.nlm.nih.gov/28657804/)
- [Flat and uphill performance correlates](https://pubmed.ncbi.nlm.nih.gov/24453532/)
- [Professional road-cyclist characteristics](https://pubmed.ncbi.nlm.nih.gov/11428685/)
- [Off- and on-bike resistance training](https://pubmed.ncbi.nlm.nih.gov/39231694/)
- [Short-sprint versus heavy strength training](https://pubmed.ncbi.nlm.nih.gov/31555153/)
