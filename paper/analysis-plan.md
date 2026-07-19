# Analysis plan

## Primary estimand

The primary unit is a distinct task represented by a role-swapped mirror pair.
For arm `a` and task `t`, `Y[a,t]` is one only when both mirror items receive
the exact gold localization. The paired risk difference is:

```text
Delta = mean_t(Y[M4,t] - Y[G3R,t])
```

The sole confirmatory test is an exact two-sided McNemar test at alpha 0.05.
The risk-difference interval is a paired task bootstrap with 10,000 draws and
seed `20260715`. Percentile endpoints use Hyndman-Fan type 7 quantiles.

Only the bound, prediction-sealed main run enters this estimand. Fake-client
attempts and the required ten-task live development run are excluded. G2
retains the completed protocol-clean development audit and its exact exclusion
candidate, while `main-output-zero` scans only the bound main-run tree. It does
not require deletion of development evidence.

Every scheduled primary pair remains in the intention-to-treat denominator.
Resolver abstention and terminal resolver `system_failure` are unsuccessful.
Never-started pending work is not converted into an outcome. A pending prefix
must be resumed or retained under the audit-only closure; it cannot receive a
prediction seal or unseal gold. Any protocol violation is likewise audit-only
and ineligible for outcome analysis. `audit-only-closure.json` binds the
candidate audit-seal hash and `audit-only-binding.json` joins that closure to
the published candidate. Either surviving decision record blocks prediction
sealing. `audit-seal.json` alone is not evidence that audit-only was chosen.
This closure is locally fail-closed; if an operator deletes the entire local
closure evidence set, the local verifier cannot prove the earlier choice.
Stronger irreversibility therefore depends on external immutable retention or
commitment.

Logical-role completion is the fraction of all manifest-scheduled model roles
across primary, control, and challenge items that end in a schema-valid
`success`. Executors and physical retries are excluded. A successful
`abstain` counts as completion. An exhausted retry is terminal for scheduling
and is preserved as `system_failure`, but it is not a completed logical role
for the 95 percent gate. This definition keeps logical-role completion
distinct from primary final-state coverage.

The confirmatory track requires all of the following:

- at least 40 eligible distinct mirror tasks
- at least 95 percent logical-role completion
- 100 percent primary item-arm final-state coverage
- zero protocol violations
- a complete terminal schedule with no open execution intent
- a marker-last prediction seal written before gold or pair-map unseal whose
  receipt hash binds the exact complete G3 verification receipt
- a committed post-seal anchor that descends from the recorded pre-run anchor
  and binds the audit tree, execution-intent tree, ledger, predictions, and
  execution evidence

A complete, protocol-clean, prediction-sealed main run that misses the
95 percent successful logical-role threshold is feasibility-only. Its terminal
failures remain in the intention-to-treat outcomes. The exact McNemar test is
not calculated or emitted for a feasibility or fake-client track. Point
estimates and intervals from those tracks are marked exploratory in every
tabular artifact. Incomplete or protocol-violating runs do not enter this
fallback; they remain audit-only and never unseal gold.

The complete-case sensitivity analysis retains a primary task only when both
arms have semantic final labels for both mirror orientations. It repeats the
paired risk difference and paired bootstrap interval, reports the excluded
task count, and performs no additional confirmatory test.

## Secondary and challenge results

Secondary results include item-level exact accuracy, five-way macro-F1,
role-swap consistency and equivariance, candidate/oracle and display-order
asymmetry, both-clean false accusation, both-faulty single-side collapse,
ambiguity challenge behavior, coverage and failure states, actual token and
latency usage, executor test count, resolver repair and corruption, provisional
to final transitions, and selective accuracy by confidence.

Per-item accuracy and F1 intervals use task-stratified cluster bootstrap. The
resampling unit is the distinct task within its locked construction stratum,
with 10,000 draws, seed `20260715`, and type 7 percentile endpoints. Five-way
macro-F1 always averages the fixed five semantic labels. A fixed label with no
true or predicted instances contributes zero. Abstention and system failure
contribute false negatives but no semantic false positive. The constructed
five-way mixture is descriptive and is not presented as a population
prevalence estimate.

S1 is the output of the fixed role `g3r_generalist_1`. A missing terminal S1
output is `system_failure`. G3 strict plurality and the deterministic M4 merge
use the rules in `design-v2.md`. S1, G3 strict plurality, and the M4 merge are
always published as diagnostics and are never additional primary arms.

Mirror role-swap consistency has all scheduled primary pairs in its
denominator. Its numerator requires two semantic final labels related by the
predeclared Candidate/Oracle label-swap transform. A pair containing
abstention or system failure is inconsistent. Swap equivariance uses the same
numerator but only pairs with two semantic final labels in its denominator.
Thus the first metric penalizes missing semantic coverage and the second
describes transformation behavior conditional on semantic completion.

Directional asymmetry is candidate-fault gold accuracy minus oracle-fault
gold accuracy over primary items. Display-order asymmetry is Candidate-first
accuracy minus Oracle-first accuracy over primary items. Both-clean,
both-faulty, and ambiguity challenge rates retain every scheduled item in
their stratum denominator, including abstention and system failure.

Physical-attempt failure rates use all model attempts in the arm as the
denominator and separately report `schema`, `transport`, `timeout`,
`client_exit`, and `weekly_quota`. Terminal logical-role failure rates use all
scheduled logical roles in the arm as the denominator and exclude quota,
which is a pause rather than a terminal state. Token and event-latency
observation coverage are reported against all physical model attempts so
incomplete telemetry is visible rather than silently treated as zero. These
fields are diagnostic only. Missing token or event-latency telemetry never
changes failure classification, retry, logical-role completion, sealing,
primary outcomes, or confirmatory eligibility. No value is imputed. Token and
event-latency aggregates contain observed values only and must be interpreted
together with their separate coverage rates.

The paper-facing latency estimand is item-arm elapsed wall time through the
final resolver invocation end. When all three initial attempts retain
authentic raw invocation records, its start is the earliest captured start and
the interval therefore includes every later retry backoff, coordinator restart,
and quota-resume gap. If a crash leaves that proof incomplete, the start is the
exact UTC instant of the earliest later matching durable full three-role wave,
captured immediately after all three child processes were polled live and
before any prompt was released. That fallback is a conservative lower bound:
it includes gaps after its proof instant but excludes any earlier crash,
restart, and backoff time. The run receipt separately counts raw-timing and
coordinator-process-wave proofs, so the basis of any pooled per-arm mean and
median remains visible. A production arm with neither three authentic initial
intervals nor one matching durable full three-key wave is unverifiable.

Summed physical invocation seconds and event-reported latency are retained as
resource and telemetry diagnostics and are never labelled end-to-end latency.
Interrupted attempts add neither duration nor optional telemetry to those
sums. A retry after an interruption still receives the fixed runtime backoff,
but the verifier does not invent the missing predecessor end needed to report
an observed retry-delay interval. Item-arm elapsed time is likewise observed
only when the highest durable resolver attempt has an authentic raw end. An
earlier resolver end never substitutes for an interrupted final attempt. At
runtime, each multi-role production wave
registers its actual child processes and requires all of them to remain live
before prompts are released. The G3 overlap claim remains explicitly limited
to one complete three-role upstream scheduler wave. It is proven either by
positive common initial raw wall-clock overlap or by the earliest matching
full pre-prompt journal event whose three physical attempts exist. Partial
retry subsets use the same runtime liveness gate and may be journaled, but are
not promoted into a paper-facing overlap claim.

Selective accuracy is reported at the fixed confidence thresholds 0.0 through
1.0 in increments of 0.1. Coverage always uses all scheduled item-arm finals
as its denominator; accuracy uses only semantic finals at or above the
threshold.

## Interpretation boundary

A positive result supports evidence-routed specialization only for this fixed
matched-depth protocol and dataset. A null result is reported with its estimate
and interval and is not evidence of equivalence. A negative result may show
that information partitioning and specialist roles harmed performance in this
setting. No result is interpreted as a model comparison.

Controls and ambiguity challenges are reported separately from the primary
superiority denominator. Gate-to-M4 screening remains exploratory and is
restricted to the synthetic candidate-mutation stratum with independently
established clean oracle status.
