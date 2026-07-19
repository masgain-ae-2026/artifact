# G3R and M4 protocol design

## Comparison

Both arms use the requested Terra model at high reasoning effort, four model
invocations, one parallel upstream layer, one resolver layer, and the same
deterministic executor. The estimand therefore concerns complete adjudication
protocols. It is not a model-only or topology-only comparison.

```text
upstream 1 --+
upstream 2 --+--> symmetric executor --> resolver
upstream 3 --+
```

For each item-arm, the runner prepares the three upstream calls at a worker
barrier. Immediately before each real child-process creation, the durable
intent advances from `started` to `dispatched`. A launch gate then registers
all three child processes and requires each one to remain live before releasing
any prompt through standard input. This is actual child-process overlap, not
merely concurrent futures. Gate failure aborts, kills, and reaps the wave.
After release, the runner joins every call already in flight and only then
commits immutable attempt records in canonical role order. A retry wave
contains only roles whose prior physical attempt is retryable. After one fixed
five-second wait, every multi-role retry wave uses the same child-liveness
gate. A quota response pauses before the executor, after every
already-dispatched peer result has been joined and preserved.

The append-only scheduler is layer-aware rather than completion-order-aware.
Upstream attempts may interleave by role across retry or quota-resume waves,
but the executor cannot start until all three upstream logical roles are
terminal. The resolver cannot start until the executor is complete. One
item-arm holds the run mutation lease throughout these layers, so another
runner or sealer cannot enter while its parallel calls are in flight.

G3R contains three independent generalists. Each receives the full
specification and both role-labelled programs. The display order of the two
program blocks is independently balanced. No generalist receives another
generalist's report.

M4 contains three independent partial-view specialists.

| Role | Receives | Must not receive |
|---|---|---|
| Spec Analyst | specification | either program, gold, other reports |
| Candidate Critic | specification, Candidate | Oracle, gold, other reports |
| Oracle Critic | specification, Oracle | Candidate, gold, other reports |
| Resolver | specification, both programs, three reports, executor evidence | gold, mirror mate, other-arm output |

Each upstream report may contribute at most three evidence slots and at most
two executable claims. The shared executor applies no more than six claims per
arm to both programs symmetrically. An agent's expected output is never treated
as truth. The executor records actual output, exception, timeout, equality or
divergence, invalid-input state, and claim provenance.

An executable input is a strict JSON array using the positional-argument
encoding of a HumanEval+ `base_input`. It need not be an existing benchmark
row. The executor accepts no agent-selected entry point. It receives the
recorded task entry point separately from the public execution manifest.
Candidate and Oracle are each launched in a fresh Bubblewrap namespace with the
same command and limits. The namespace has no network and does not mount the
repository, home directory, raw root, or private root. It binds only the system
Python runtime and a content-hashed runner read-only. Executor identity includes
the Bubblewrap, Python, and runner SHA-256 values.

JSON Schema validation is the first output-validation layer. A hash-bound role
semantic validator then parses every executable-input string as strict JSON,
requires a top-level positional-argument array, rejects repeated slot IDs,
checks role-local evidence kinds and limits, and checks each resolver evidence
reference against the exact allowed-reference set in that item. A failure in
either layer is an invalid final output under the same fixed retry rule. The
semantic validator and its hash are part of the recorded protocol identity.

## Labels and provisional decisions

G3R upstream and both final resolvers use the five semantic labels
`candidate_only_fault`, `oracle_only_fault`, `both_faulty`, `neither_fault`,
and `specification_ambiguous`, plus `abstain`.

M4 upstream roles use local states. The Spec Analyst reports `determinate`,
`materially_ambiguous`, or `uncertain`. Each critic reports `consistent`,
`faulty`, or `uncertain`.

The G3R provisional decision is defined only when all three upstream slots
contain valid semantic reports. Any missing report or `abstain` produces
`unresolved`. Otherwise a label is returned only when it receives at least two
of the three votes; a three-way split produces `unresolved`.

The M4 provisional decision uses the following complete precedence rule. Any
missing upstream report produces `unresolved`. With three valid reports,
`materially_ambiguous` maps to `specification_ambiguous`. Otherwise an
`uncertain` Spec Analyst or either `uncertain` critic produces `unresolved`.
For a `determinate` specification, Candidate/Oracle critic states map as
follows: `faulty/consistent` to `candidate_only_fault`, `consistent/faulty` to
`oracle_only_fault`, `faulty/faulty` to `both_faulty`, and
`consistent/consistent` to `neither_fault`.

`system_failure` is an execution state, not a semantic label. Unauthorized
tool activity, requested/reported model mismatch, or gold access is a
run-invalidating `protocol_violation`.

## Invocation isolation

Every logical role runs with one item in a fresh empty Git repository through
an ephemeral Codex session. The production driver ignores user configuration
and rules, selects a read-only sandbox, reads the prompt from standard input,
and records JSONL events. The runner rejects API and access-token variables and
requires a redacted login status that identifies ChatGPT authentication.
The raw invocation keeps the full canonical non-local executable identity and
its pinned hash. The separately redacted command replaces the machine-local
executable path with the pinned production basename `codex`, and replaces only
the schema and fresh-repository paths with fixed placeholders. The diagnostic
assessment projects the canonical executable identity to its basename. G3
verification recomputes both projections exactly while continuing to require
the unprojected identity and hash in the raw invocation.

The schema loader takes one stable schema-file snapshot. The exact same bytes
are parsed, hashed into protocol identity, copied into a mode-0400 memfd, and
passed to the child through `/proc/self/fd`. The memfd is kernel-sealed against
write, growth, shrinkage, and seal changes. The production Codex and Git
executables are opened from stable unique identities, hashed, copied into
executable memfds with the same seals, and launched through their descriptors.
This closes path replacement between verification and execution. The
production path fails closed if memfd creation or sealing is unavailable.

Read-only Codex configuration is not itself evidence of no tool use. The event
stream is inspected, and any shell, web, MCP, or other tool event invalidates
the run. Mirror mates, multiple items, session resume, and context reuse are
not allowed inside one model invocation. Concurrent invocations remain
separate ephemeral processes and repositories.

## Persistent main coordinator

The production batch command defaults to three item-arm workers and retains
one exclusive run lease plus one verified ledger append session for its
process lifetime. It performs the full fixed
manifest, source, anchor, intent, and ledger-prefix authentication once at
startup. Constant-time identities then guard those authenticated inputs before
each transition. `--item-arm-workers N` creates a bounded worker pool; the
coordinator allocates the earliest incomplete scheduled item-arms to durable
slots and refills a slot only after observing all workers that have already
finished at that boundary.

Workers never append the ledger directly. Attempt publication remains
item-local and immutable, while each ledger request is returned to the
lease-owning coordinator and serialized into the one verified hash-chain
session. Ledger entries from different arms may therefore interleave.
`execution_schedule_progress` projects the chain by scheduled item-arm,
validates every arm-local upstream, executor, resolver, attempt, retry, and
terminal transition, and returns the first incomplete arm only after rejecting
any arm-local violation. Manifest allocation order remains fixed; completion
order is measured rather than prescribed.

This procedure does not weaken invocation isolation. The retained client is
only a factory-approved transport object. Every call still creates a new
temporary directory, initializes a fresh Git repository, invokes one
`--ephemeral` Codex session, and discards it. No prompt, context, thread, or
session is reused within or across arms. Each arm retains its own three-role
child-liveness barrier, local executor, and subsequent resolver.

One coordinator-journal epoch represents one worker-execution phase beginning
after orphan-call recovery and immediately before allocation. Its published
self-hashed event chain records the worker bound, exact manifest schedule
position and item-arm of each slot, production live-wave facts, and the sole
terminal transition for each quiescent slot. Published events are append-only;
incomplete private journal write workspaces are cleanup state, not evidence.
Starting replacement worker execution appends a new epoch even when its
predecessor is open; the predecessor state hash binds the complete crashed
execution state. A crash while recovering the predecessor appends no empty
worker epoch and resumes the same idempotent recovery on the next execution.
Closed epochs require all allocated slots to be terminal. A completed
concurrent run requires the newest epoch to be closed, while older open epochs
remain the immutable crash facts used by recovery.

The mode boundary is bidirectional and fail-before-mutation. A first
concurrent epoch cannot be created after any journal-less one-worker intent
evidence exists. Conversely, journal absence is accepted only for a legacy
serial ledger whose item-arm blocks are contiguous in manifest order and whose
intents contain no coordinator allocation binding. Thus deletion of a
coordinator journal cannot downgrade a completed concurrent run into a valid
serial run even when its ledger happened to finish in arm order.

Recovery authenticates the whole in-flight publication-staging set read-only
before the coordinator changes a ledger or journal record. A process
loss after a ledger rename but before the redundant intent completion marker
is repaired only after a read-through of the exact ledger entry and logical
call ID. Any still-dispatched model intent without a complete publication is
recoverable only when its exact item-arm has a nonterminal slot in an open
journal epoch. The replacement reconstructs the deterministic call identity,
then publishes an explicit interruption attempt with classification
`retryable_infrastructure`. It does not create raw invocation, capture, event,
usage, timing, or thread evidence. The concurrent coordinator never promotes
unpublished attempt staging, even when its attempt record is complete, because
the result did not cross the coordinator publication boundary. A publication
workspace may be adopted only when its attempt key is the unledgered dispatched
model call of an open crashed slot. The crash-resumable adoption transaction
moves its files below the interruption attempt, hashes every retained byte into
the attempt record, normalizes byte-free directory residue, and never
interprets those fragments as raw telemetry.
Unmatched staging is retained in place and makes the concurrent boundary
return `audit_only` with reason `incomplete_attempt_publication`. The ordinary
single-retry rule applies only after a complete interruption is published.
The evidence journal does not itself supervise orphan operating-system
processes. Before a crash resume, the operator must terminate and verify the
absence of the original coordinator process group. A parent-only `SIGKILL`
does not prove its dispatched Codex children ended and is not an admissible
resume procedure. Emptying the local process group also does not prove remote
provider cancellation, absence of accepted work, or absence of billing.

For a multi-role production wave, the launch gate polls all registered child
processes, captures UTC immediately after the successful liveness sweep, and
blocks prompt release until the coordinator has durably appended the exact
physical attempt keys and captured instant to the slot. Raw attempt intervals
remain the primary overlap proof. If an initial wave is only partly published
before a crash, the earliest later durable full three-role scheduler wave can
prove that its exact children were live together; missing attempts remain
telemetry-free interruptions. An arm with neither an initial raw proof nor a
later complete journal proof fails production G3 verification.

## Retry and quota states

Semantic outputs are never retried. A transient transport failure, timeout,
nonzero client exit, or missing or invalid final schema receives at most one
retry with the identical content IDs. A weekly quota response pauses the
entire scheduler and leaves the triggering role and unstarted queue pending. It
does not consume the retry. A changed protocol, dataset, prompt, schema, model,
or client identity requires a new content-run ID.

The one eligible retry waits for a fixed five-second backoff. The production
runner uses the captured system sleep function; test fixtures may replace only
the sleeper while retaining the same five-second argument.

Each resolver upstream slot contains either a schema-valid report or the exact
missing marker `{"missing":true,"failure_class":"<class>"}`, where `<class>` is
one of `transport`, `timeout`, `client_exit`, or `schema`. The marker represents
an exhausted upstream `system_failure`; it supplies no semantic evidence and
makes the pre-resolver decision `unresolved`. A scheduled resolver is still
called. An exhausted resolver produces terminal `system_failure` for that
item-arm.

Missing token-usage fields or event-reported latency are not missing-output
markers and never trigger a retry. They are diagnostic-only telemetry. They do
not affect failure classification, scheduler terminality, logical-role
completion, G3 sealing, or confirmatory eligibility. Aggregates sum only
observed values and report observation coverage; no missing telemetry is
imputed as zero. Required local capture timestamps remain the source for
wall-clock scheduling and item-arm elapsed time.

Logical-role completion counts only schema-valid successful role outputs.
An exhausted role is terminal for the append-only scheduler but is not a
completed role for the fixed 95 percent analysis gate. A run prefix abandoned
with pending work, an unresolved dispatched intent, or a protocol violation is
audit-only. Under the run lease, `seal --audit-only` first computes the exact
candidate audit receipt, writes `audit-only-closure.json` binding its hash,
publishes that exact candidate as `audit-seal.json`, and writes
`audit-only-binding.json` last to bind the closure to the candidate.
`audit-seal.json` alone is only a candidate, not an audit-only decision. Either
surviving decision record blocks later prediction sealing. The closed prefix
receives no prediction seal, gold unseal, or outcome analysis. This is a local
fail-closed guarantee. Deletion of the entire local closure evidence set is
outside the verifier's enforcement, so a stronger irreversible claim requires
external immutable retention or commitment.

## Program-review surplus cap

Every machine-eligible clean parent remains in blind program review. Fault
candidates are capped only after terminal witness verification. Within the
verified returned-witness set, candidates are sorted by their already frozen
global mutation position. The first returned witness under each clean parent
is the target, the second is its backfill, and later returned witnesses under
that parent are surplus. Both selected slots enter primary review at the same
time.

The target and backfill assignment is fixed before any human response. A later
human verdict or independent-test outcome never causes an omitted witness to
replace either slot. If both selected candidates attrit, that parent supplies
no qualified fault. The private operator index records the policy identifier,
per-parent limit, selected target/backfill rows, omitted rows, global mutation
positions, and aggregate available, selected, and surplus counts. The complete
witness archive remains unchanged, so omitted candidates remain auditable but
outside the program-review estimand.

With at most 228 clean parents, this rule permits at most 228 clean programs
and 456 returned-fault programs in primary review. Two independent primary
reviewers therefore face at most 1,368 primary judgments before any staged
resolver disagreements.

## Recording boundary

The preparation transaction base is a separate trust boundary. Preparation
requires quiescent, exclusive single-operator ownership of that base. The
operator records its `st_dev:st_ino` identity and exact entry set immediately
before and after publication. The FD-pinned run-root capability guarantee
starts at the published run and does not protect the preparation base itself
against a malicious concurrent local replacement.

Fresh run-guard and manifest-directory publication requires atomic directory
`renameat2(RENAME_NOREPLACE)`. Before reserving an execution intent, before
every intent transition, and before any interrupted-intent recovery mutation,
the runner resolves the filesystem type from the pinned run-root descriptor
and accepts only native Linux ext4. WSL DrvFs/v9fs therefore fails both the
fresh publication primitive and the active-root gate. The gate also performs a
pathless, non-mutating `renameat2` probe and accepts only the expected
missing-path result, proving that the running libc and kernel expose the
required flag. An existing copied guard or reserved intent cannot bypass that
gate before a physical call. Falling back to an ordinary rename after an
absence check would permit a concurrent empty destination directory to be
replaced and would contradict the append-only evidence boundary. A DrvFs copy
may therefore serve only as a hash-verified backup, not as an execution root.

The public runner has no private-root argument and must observe
`MASGAIN_PRIVATE_ROOT` as unset. Original event streams live outside the
repository under `MASGAIN_RAW_ROOT`. Each attempt is written to a private
temporary directory and atomically renamed into an append-only final path.
Completion entries form a canonical hash chain. No attempt is overwritten.

G2 requires the completed protocol-clean ten-task live development audit and
binds its exact exclusion candidate into the main preparation record. Its
`main-output-zero` check scans only the bound main-run tree. Development and
fake-client evidence never enters the main estimand, but the retained live
development evidence is not erased or treated as forbidden main output.

The main item order is derived from one recorded seed and the exact opaque
mirror-pair relation. The deterministic producer records the first rejection
counter whose hash-ranked order keeps mirror mates nonadjacent. It also
balances which arm is executed first. The verifier reconstructs the mirror
relation from the bound public programs and reproduces the same schedule.

Immediately before a subprocess starts, its durable execution intent moves
from `started` to `dispatched` in a write-once record. Completion is accepted
only from that state. An unresolved dispatch outside an authenticated open
concurrent slot remains audit-only and is never called again. A dispatch in an
open crashed slot is first converted into an immutable unknown-result
interruption attempt; only that explicit retryable outcome can advance the
ordinary retry rule. The G3 verifier requires positive common overlap for the
initial three-role layer. It uses all three raw invocation intervals when they
survive. Otherwise it may use the earliest full pre-prompt, gate-captured
live-wave event bound to three exact physical attempt keys, whether that is the
partly lost initial wave or a later full retry wave. Partial retry waves use
the same runtime gate and may also be journaled, but are not promoted into a
paper-facing overlap claim.

Prediction sealing reconstructs the exact complete G3 receipt and binds its
hash into the seal. It writes the canonical ledger, pre-gold predictions,
execution evidence, and prediction digest first, then writes
`prediction-seal.json` as the final marker. A pre-existing marker is valid only
with the complete exact sibling inventory.

The C1 fake-client slice proves these data shapes and state transitions only.
It is not live model evidence and does not open G1 or G2.
