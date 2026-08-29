# Normative Study Design for a Regulated Cognitive Instrument

For projects where norms do **not** yet exist. If they do, read
[evidence-conversion.md](evidence-conversion.md) instead.

## The rule that constrains everything else

**The intended population may never be broader than the normative coverage.**

Write the intended-use population sentence *first*, then design the sampling
frame to cover it. Doing it the other way round produces a gap that is only
discovered while drafting the submission — see pitfalls.md §3 for a real case
where a 26–64 year-old gap went unnoticed through three planning revisions.

Before collection, list the age bands the product will claim, and check that
every band has a stratum. Common failure: sampling by convenient institutions
(primary school, junior high, senior high, university, community elders) which
silently omits working-age adults.

## Stratification

Stratify by **age band × years of education**. Education is not optional for
cognitive norms — it is frequently a larger source of variance than age within
adult bands.

Typical target: 100–150 per stratum, giving 600–900 total for a five-band
design. Treat these as planning figures and re-derive from the observed variance
of the actual tasks in the statistical analysis plan.

Additional strata to consider: literacy, primary language, and device
familiarity — all of which confound reaction-time measures in older cohorts.

## What must be reported

- Internal consistency
- **Test–retest reliability (ICC)** — from a dedicated subsample, n ≈ 50–80,
  2–4 weeks apart. Plan it into the main collection; retrofitting it costs
  6–7 months (see evidence-conversion.md).
- Convergent validity against established instruments (e.g. MMSE / MoCA / CASI
  for cognitive screening)
- Norm tables by age × education
- **MDC and RCI** — minimal detectable change and reliable change index

## Why MDC/RCI is the load-bearing statistic

A percentile answers "where does this person stand". Only MDC/RCI answers
"is this person's change real, or is it measurement error". Any longitudinal or
trend-tracking claim — which is usually the commercial point of a digital
cognitive test — rests entirely on it.

**No RCI, no trend claim.** Decide early whether the product's value
proposition depends on trend detection, because that determines whether the
retest subsample is a nice-to-have or a gating requirement.

## Administrative lead time people forget

- Minors require guardian consent; school-based recruitment needs education
  authority and school approval on top of IRB.
- Elderly community recruitment usually needs exclusion of existing dementia
  diagnoses, and a documented protocol for the uncontrolled setting.
- Personal data protection and human-subjects research law apply throughout.
- **Decide the data architecture (on-device vs cloud) before collection.** It
  simultaneously determines the cybersecurity file, the privacy compliance
  scope, and the QMS boundary. Changing it later invalidates documentation in
  three places at once.
