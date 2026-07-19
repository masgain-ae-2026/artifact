# MAS-GAIN 2026 anonymous V2 R4 artifact refresh

This directory stages the anonymous evidence needed to review the V2 paper.
It contains the R4 paper in IEEEtran and acmart formats, the recorded protocol,
the analysis plan, preserved historical records, five successor audit receipts,
an independent exact-power enumeration, and seven redacted record-level indexes
for the executed stages.

The indexes retain content hashes, hashed record identities, categorical
dispositions, and countable summaries. They omit source code, task names,
prompts, suite inputs, observed outputs, paths, timestamps, durations, model and
machine identity, reviewer identity, responses, and rationales.

The source-object hashes bind each extract to the preserved evidence closure.
This gives the study an internally auditable trail and makes accidental or
careless substitution hard. It is not tamper evidence against a motivated
operator who controls that closure. The study used no external anchor.

## Paper and protocol

- `paper/masgain26-submission.pdf` is the eight-page anonymous IEEEtran R4
  paper. Its SHA-256 is
  `cf5874d3d685ba0123f4b27bab56b52aacbc5f07668f1a259bf308ea6d1c5223`.
- `paper/masgain26-submission-acm.pdf` is the eight-page anonymous acmart R4
  paper. Its SHA-256 is
  `db509b0a74b7ea29b6bb93439b05db1aba6f790909915d8cd225ea39f13c2ffb`.
- `paper/design-v2.md` records the G3R and M4 protocol contract.
- `paper/analysis-plan.md` records the primary estimand and analysis rules.

## Receipts

- `receipts/2026-07-18-c3-evidence-constrained-pilot.json` is the canonical C3
  deviation receipt. Its raw SHA-256 is
  `77164ee6445723cfa1fd5c7583701705ac156a19e20add9fff7b1794a2f36dab`.
- `receipts/corrected-selection-receipt.json` binds the canonical C3 content
  hash, `a6dc580565e1da9142df6e99afab53782df618977599027063430509a3bfc63e`, and records the
  corrected 51-item selection, eight paired tasks, 408 planned model calls,
  zero calls performed by selection, and zero human-gold records.
- `receipts/superseded-selection-receipt-unit-accounting-error.json` preserves
  the historical receipt that incorrectly used all 51 selected items as paired
  tasks. Its raw SHA-256 is
  `ef9192884f95e4f271c1348848f15133a28a295c80a384b3a8c1be52d8b54980`.
- `receipts/2026-07-19-unit-accounting-successor.json` links that preserved
  predecessor to the corrected eight-mirror receipt and binds the stop. Its
  raw SHA-256 is
  `911009b1d89cca2a6e8e95ce3e7aec25c1c8a6b7c4e7e9645903e243ceed7f5f`.
- `receipts/2026-07-19-promotion-attrition-accounting.json` conserves all 277
  reviewed programs across 101 qualified clean programs, 69 qualified fault
  programs, 18 plan exclusions, 88 duplicate-source exclusions, and one
  independent-test non-pass. Its raw SHA-256 is
  `cbae106c848f0cdde4772bfce3b5f55d8accd61307f352d5c41e9d41ca6e1ab9`.
- `receipts/2026-07-19-power-plan-adequacy-successor.json` records the
  independent audit of the original resource target. It preserves the stated
  alternative and records power of 0.5249353223627345 at 60 pairs and the first
  target-power sample size of 103 pairs. Its raw SHA-256 is
  `4ffc36525345e8d0872568b9b1300e48f249b1aebe8c316b53c1393bd589d2d1`.
- `receipts/2026-07-19-c3-selection-audit-successor.json` records the
  lexicographic selector re-audit. It reports 15 mirror tasks without
  supplemental minima and 14 under either one-per-stratum minima or the
  historical quotas. The audit made no model call and did not enter final gold.
  Its raw SHA-256 is
  `1d632c1340be31d21df78a6c63d26337c2e54ef6fcc8819141b1e4a13a3af883`.
- `receipts/2026-07-19-r4-methodological-audit-successor.json` is the append-only
  R4 successor. It corrects the chronology and analysis-unit characterization,
  reconciles the historical 8, corrected 14, and identity-ceiling 15 counts,
  and binds both exact-power implementations. Its raw SHA-256 is
  `f9fdf97c507281d16c868a9d4299e7d44f48e55277e0c6d89602a4970616472c`.
  Its content receipt SHA-256 is
  `b33704c1a931f6ea2292e03cbda70cfbd497e35c7760ad28a9e6813ac4c64f1b`.

The `pre_registered_allocations` key in the C3 receipt is an internal schema
label. It does not claim an external registration or external anchor.

## Reviewer indexes

Each JSON summary can be recomputed by counting its record array and grouping
the stated categorical fields.

- `indexes/01-construction.json` proves 114 tasks, 228 jobs, 230 physical
  attempts, 228 accepted sources, one retryable infrastructure attempt, and one
  quota pause.
- `indexes/02-mutation-freeze.json` proves 228 parents, 6,218 frozen mutations,
  zero executions, and no outcome access.
- `indexes/03-qualification.json` proves 456 clean suites, 6,218 mutation
  suites, 6,674 terminal jobs, 417 clean-suite agreements, 39 clean-suite
  disagreements, 692 mutation survivors, and 5,526 detections.
- `indexes/04-witness.json` proves 692 input survivors, 58 exclusions, 634
  terminal suites, 217 returned-output witnesses, and 417 other outcomes.
- `indexes/05-program-review.json` proves 196 machine-clean programs, 81 fault
  candidates, and 277 packets with two primary response hashes each.
- `indexes/06-panel-verdict.json` proves 275 primary agreements, two resolver
  decisions, 193 correct verdicts, 80 faulty verdicts, and four materially
  ambiguous verdicts.
- `indexes/07-independent-test.json` proves 180 terminal jobs with two fresh
  cases each, 179 agreements, and one disagreement.

Promotion is supported by the C3 receipt, which records 101 qualified clean
programs and 69 qualified fault programs. The historical total-item-first
allocation contained eight pre-gold mirror candidates. The unit-first re-audit
found 14 under the same pilot quotas and 15 without supplemental minima.

## Independent exact-power audit

- `audit/independent_power_enum.py` uses the Python standard library only and
  does not import the repository helper. Its SHA-256 is
  `ceb11836339e8d70a3a12622f6686cc52041197186ad93298a04c6247f000b05`.
- `audit/INDEPENDENT-POWER-AUDIT.md` records the independently reproduced
  powers, MDE values, all-count check for `n <= 15`, and both implementation
  hashes. Its SHA-256 is
  `d18a37cb562aec9cc3200036df0f2fc92fec32b1e76544a414b240e2afd37388`.

## Family inventory hashes

Construction, qualification, witness, and independent-test indexes also bind a
family inventory. Files are ordered by their relative POSIX paths. Each inventory
line contains the file SHA-256, two spaces, the relative path, and a line feed.
The family hash is the SHA-256 of the concatenated lines. Relative paths begin
with `attempts/`. No absolute path is retained.

The four family hashes are as follows.

- Construction with 230 assessment records
  `de3317157b32c82abf561e04d3133c586c48477a1641f4a54728f91d7a57bf61`
- Qualification with 6,674 result records
  `3404b55cc8b3a615885216270ba2289ea9535281d0f49e88b2300147342826bf`
- Witness with 634 result records
  `16c2fa930e0c4c65fc1861d0919d14e2320619c2bf77ecb958b9dc8bafc1c815`
- Independent test with 180 result records
  `26e49d3183c2112d0be6dcd7cf3ec285a187de7837a98ad28854841a1441e085`
