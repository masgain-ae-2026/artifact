# MAS-GAIN 2026 anonymous V2 artifact

This package supports the current manuscript, *Counting Before Calling:
Receipt-Gated Analysis-Unit Accounting for a Stopped Multi-Agent Adjudication
Study*.

The `paper/` directory holds the current manuscript,
`counting-before-calling.pdf`. Two manuscript copies with an earlier title
were removed in an earlier commit.

The package preserves redacted stage indexes and append-only receipts, an
independent exact-power enumerator, the repository power helper and its focused
tests, postmortem sensitivity code and stored output, a postmortem adequacy
validator, and the available selector audit source. The validator and
sensitivity analysis were implemented after the stopped study. They do not
retroactively change the historical protocol or constitute study output.

The indexes retain content hashes, hashed record identities, categorical
dispositions, and countable summaries. They omit task names, prompts, suite
inputs, observed outputs, local paths, timestamps, durations, model and
machine identity, reviewer identity, responses, and rationales. The hashes are
local commitments without an external timestamp or transparency anchor.

## Package map

- `indexes/01-construction.json` through `indexes/07-independent-test.json`
  are redacted record-level stage indexes. The program-review index includes
  the aggregate primary-label matrix and kappa inputs without per-packet
  labels.
- `receipts/` contains the historical selection records and append-only
  successor audits.
- `audit/independent_power_enum.py` is the independent standard-library exact
  power verifier.
- `audit/postmortem_sensitivity.py` and
  `audit/postmortem-sensitivity-output.json` provide a reproducible sensitivity
  boundary check and its canonical-LF expected output.
- `audit/postmortem-sensitivity-grid.md` preserves the complete sensitivity
  grid and verdict-boundary output from the package audit.
- `enforcement/` contains the postmortem typed-unit validator, schema fragment,
  command-line boundaries, tests, and one-command reproduction.
- `study/mas_review/src/mas_review/statistics.py` is the repository power
  helper whose SHA-256 is pinned in the methodological successor receipt;
  `study/mas_review/tests/test_statistics.py` is its focused test suite.
- `study/mas_review/tools/selection_lexicographic_audit.py` is the available
  selector audit source. It requires the private verified lineage and is
  included for source inspection, not as a runnable public reproduction.

## Reproduction

Run these commands from the repository root with Python 3.11 or later. They
use only the standard library and make no network or model calls.

```console
python -m unittest discover -s enforcement/tests -v
python -m enforcement.reproduce
python audit/independent_power_enum.py
python -m unittest discover -s study/mas_review/tests -p test_statistics.py -v
python -c "import pathlib,subprocess,sys; got=subprocess.check_output([sys.executable,'audit/postmortem_sensitivity.py']).replace(b'\r\n',b'\n'); expected=pathlib.Path('audit/postmortem-sensitivity-output.json').read_bytes(); print('PASS' if got==expected else 'FAIL'); raise SystemExit(got!=expected)"
```

Expected terminal results are `OK`, `RESULT PASS`, JSON with
`"status":"PASS"`, `OK`, and `PASS`, respectively. The enforcement controls
use synthetic interface data only for positive paths; they are not study
evidence.

## Evidence grading

`D` means directly recomputable from public package files, `R` means recorded
in a preserved receipt, `P` means partially supported, and `M` means not
included. The package audit before this refresh counted `D=13, R=10, P=7,
M=12`. The mapping below counts `D=16, R=10, P=11, M=5` after this refresh.

## Claim-to-file mapping

| ID | Current-manuscript claim | Package evidence or absence | Grade |
|---:|---|---|:---:|
| 1 | Construction: 114 tasks, 228 jobs, 230 attempts, 228 accepted, one retryable and one quota pause | `indexes/01-construction.json` | D |
| 2 | Freeze: 228 parents, 6,218 mutations, zero executions | `indexes/02-mutation-freeze.json` | D |
| 3 | Qualification: 456 clean plus 6,218 mutation suites; 417/39 clean outcomes and 5,526/692 mutation outcomes | `indexes/03-qualification.json` | D |
| 4 | Clean disagreements: base 7 and withheld-plus 32 | `indexes/03-qualification.json` | D |
| 5 | Clean disagreements span 32 programs; seven programs have both kinds | Not included: program identities are redacted, so cross-kind grouping cannot be recomputed. | M |
| 6 | Witness: 692 inputs, 58 exclusions, 634 analyzed, 217 returned outputs and 417 other outcomes | `indexes/04-witness.json` | D |
| 7 | Program review: 196 machine-clean plus 81 fault candidates; 275 primary agreements and two resolver cases | `indexes/05-program-review.json`; `indexes/06-panel-verdict.json` | D |
| 8 | Primary-label matrix `[[193,0,0],[1,80,1],[0,0,2]]`, agreement 0.9928, kappa 0.9831 | `indexes/05-program-review.json` aggregate-only matrix, marginals, and exact kappa fraction | D |
| 9 | Both resolver disagreements occur on the same median task | Not included: task identity is redacted. | M |
| 10 | Final panel: 193 correct, 80 faulty, four ambiguous | `indexes/06-panel-verdict.json` | D |
| 11 | Independent test: 180 programs, two cases each, 179 agreements, one disagreement | `indexes/07-independent-test.json` | D |
| 12 | The named disagreement example and its input/output strings | Not included: task identity, inputs, and outputs are redacted. | M |
| 13 | Promotion conservation: 277 equals 101 clean plus 69 fault plus 18 plan exclusions plus 88 duplicates plus one nonpass | `receipts/2026-07-19-promotion-attrition-accounting.json`; `receipts/2026-07-19-unit-accounting-successor.json` | R |
| 14 | Eighteen plan exclusions split 13 nondistinct, four ambiguous, one clean judged faulty | `receipts/2026-07-19-promotion-attrition-accounting.json` | R |
| 15 | Resource ceiling 50, identity ceiling 15, historical execution 8, corrected re-audit 14 | `receipts/2026-07-19-r4-methodological-audit-successor.json`; `receipts/2026-07-19-unit-accounting-successor.json` | R |
| 16 | Historical selection: 51 items, eight mirrors, 408 calls, zero gold/model calls | `receipts/corrected-selection-receipt.json`; `receipts/2026-07-19-unit-accounting-successor.json` | R |
| 17 | Superseded 51-unit denominator and 0.4488 power | `receipts/superseded-selection-receipt-unit-accounting-error.json` | R |
| 18 | Corrected selector re-audit: 63 items, 14 mirrors, 26 clean, one fault, 504 calls | `receipts/2026-07-19-c3-selection-audit-successor.json` | R |
| 19 | Selector alternatives: 15/26/0/64/512 and 14/26/1/63/504 | `receipts/2026-07-19-c3-selection-audit-successor.json` | R |
| 20 | Explicit call cap `C<=408` yields 8/26/1/51/408 | `receipts/corrected-selection-receipt.json`; `study/mas_review/tools/selection_lexicographic_audit.py` is source context, but the public package lacks the pinned lineage and explicit call-cap solver log. | P |
| 21 | Target 10/10 is infeasible; minimum 8/8 permits at most seven mirrors | `receipts/2026-07-19-c3-selection-audit-successor.json` | R |
| 22 | Forty-one flexible items split 26/6/9; raw assignment count 12,824,703,626,379,264 | `study/mas_review/tools/selection_lexicographic_audit.py` contains the DP eligibility and assignment method, but the pinned candidate projection and raw-count log are not included. | P |
| 23 | Selector DP visits 3,750 states and 89,618 transitions; exact 26/1 visits 837 and 32,083 | `study/mas_review/tools/selection_lexicographic_audit.py` contains the DP and the successor receipt records its outcomes; the instrumented counts and pinned input set are not included. | P |
| 24 | Five-run median 4.210 s and range 3.694--4.953 s | Not included: no original timing log was found. | M |
| 25 | Call-cap-only allocation admits 15 mirrors in 304 calls | `receipts/2026-07-19-c3-selection-audit-successor.json`, `study/mas_review/tools/selection_lexicographic_audit.py`, and `audit/postmortem-sensitivity-output.json` support the 15-task ceiling and eight-calls-per-item arithmetic; the pinned candidate set is not included. | P |
| 26 | Source universe 164, minus 40 Study 0 and 10 development tasks, leaves 114 | `indexes/01-construction.json` directly supports 114 only; the benchmark snapshot and identity-level exclusions are not included. | P |
| 27 | Challenge pool 10, fixed challenge mirrors 8, development exclusions 10 | `receipts/2026-07-18-c3-evidence-constrained-pilot.json`; `receipts/corrected-selection-receipt.json` | R |
| 28 | Configuration-derived remaining capacity is 1,184 calls | `audit/postmortem_sensitivity.py` and its stored output bind the source content hash and JSON pointer; the seed-bearing source configuration is not included. | P |
| 29 | Exact McNemar assumptions alpha .05, delta .2, discordance .5, target .8, required 103 | `audit/independent_power_enum.py`; `audit/INDEPENDENT-POWER-AUDIT.md`; `receipts/2026-07-19-power-plan-adequacy-successor.json` | D |
| 30 | Power at n=8/15/40/60/103 is .015753/.098285/.354433/.524935/.801819 | Same files as claim 29 | D |
| 31 | Sensitivity required n values 61/103/144 and 408/46 for the stated pairs | `audit/postmortem_sensitivity.py`; `audit/postmortem-sensitivity-output.json`; `audit/postmortem-sensitivity-grid.md` | D |
| 32 | MDE and n=8 attainability/max-power values | `audit/independent_power_enum.py`; `receipts/2026-07-19-power-plan-adequacy-successor.json` | D |
| 33 | Pre-gold adequacy gate, protected call boundary, and seven-step procedure | `enforcement/adequacy.py`, `enforcement/main_call_runner.py`, and `enforcement/reproduce.py` directly exercise the postmortem gates; the current manuscript source for the seven-step presentation is not included. | P |
| 34 | Pipeline figure from construction through adequacy and stop | `indexes/`; `receipts/`; figure source and current manuscript are not included. | P |
| 35 | Validator schema/CLI, unit-type error, supported threshold 103, seven fixtures, zero protected calls/output | `enforcement/` supplies the validator, schema, two CLIs, tests, and reproduction at threshold 103 with zero protected calls/output. The exact seven standalone inputs described by the current manuscript were not found, and the shipped refresh tests are not a byte-for-byte realization of that seven-row table. | P |
| 36 | Independent verifier does not import the repository helper; helper hash is recorded | `audit/independent_power_enum.py`; `audit/INDEPENDENT-POWER-AUDIT.md`; `study/mas_review/src/mas_review/statistics.py`; `study/mas_review/tests/test_statistics.py`; methodological successor receipt | D |
| 37 | Stop precedes human gold and main execution; no performance claim | Corrected and unit-accounting receipts plus stage indexes | R |
| 38 | Raw streams and administrative records remain outside the anonymous repository | This README and the redaction fields in the indexes | D |
| 39 | Hashes are local and have no external anchor | This README | D |
| 40 | Token use, latency, abstention, and API failures | Not included: these were not measured because the main protocol did not run. | M |
| 41 | Decision chronology across 2026-07-15, 18, 19, and 20 | The eight dated receipts support part of the chronology; same-day ordering and an external timestamp are not included. | P |
| 42 | Current seven tables and procedure source | `indexes/` and `receipts/` support numerical cross-checks; the current-title PDF/TeX and rendering/caption binding are not included. | P |

## Not included

- Manuscript TeX source. The PDF is in `paper/`; no earlier-title PDF
  remains in the package.
- The exact seven standalone validator inputs and expected-output manifest
  described by the current manuscript. The available refresh contained inline
  synthetic test construction instead.
- The selector's pinned candidate set, seed-bearing configuration, private
  verified lineage, instrumented state/transition log, and five-run timing log.
- The source benchmark snapshot and exact inclusion/exclusion task identities.
- Per-packet primary labels, task identities, prompts, suite inputs/outputs,
  local paths/times, reviewer/model/machine identities, responses, and
  rationales.
- Main-run operational metrics, because the study stopped before those calls.
- An external timestamp or transparency anchor.

The selector source is provided without its private inputs so that the method
can be inspected without exposing redacted identities or seed material. No
missing artifact has been inferred or reconstructed.
