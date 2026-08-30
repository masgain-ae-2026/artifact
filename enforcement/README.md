# Postmortem adequacy enforcement

This validator was implemented after the postmortem. The historical
51-selected-item denominator error was found by human audit. The preserved
receipts enabled that audit but did not automatically catch the error at the
time. This code prevents the same conversion from recurring at the protected
main-call boundary.

The implementation is deterministic and uses the Python standard library. It
makes zero model calls and reads no protected output. It reads receipt metadata
only. The study remains stopped. No `U_A` receipts were produced historically
because final adjudication did not run, and this artifact does not manufacture
them.

From the repository root, reproduce all controls with:

```sh
python3 -m enforcement.reproduce
```

Run the test suite with:

```sh
python3 -m unittest discover -s enforcement/tests -v
```

The adequacy interface in `adequacy.py` accepts only
`masgain-v2-typed-unit-receipt-set/v1` with outer and inner type `U_A`. It
rejects a bare integer, `U_S`, `U_MC`, `U_M`, duplicates, ineligible receipts,
noncanonical ordering, and invalid content hashes before calculating power.
The exact McNemar calculation reuses `audit/independent_power_enum.py`.

The negative control uses the byte-preserved
`receipts/superseded-selection-receipt-unit-accounting-error.json`. The direct
command is:

```sh
python3 -m enforcement.adequacy receipts/superseded-selection-receipt-unit-accounting-error.json --content-run-id 0000000000000000000000000000000000000000000000000000000000000000
```

It exits 2 with:

```text
E_UNIT_TYPE_MISMATCH: adequacy requires receipt_set<U_A>; received masgain-v2-prepared-selection-receipt/v2 with 51 mixed selected main items
```

`main_call_runner.py` recomputes the supplied decision from the exact `U_A`
set, locked analysis, and requested content-run ID before invoking its callback
or subprocess. A missing, stopped, forged, tampered, differently bound, or
cross-run replayed decision cannot cross that boundary. The reproduction also
verifies that the preserved historical STOP record is not mistaken for a new
typed PROCEED receipt. The positive 103-unit control and empty-set STOP control
are synthetic interface data, not study evidence, and invoke at most an
in-memory dry-run callback.

The compact JSON Schema fragment is `receipt-schema-fragment.json`. Runtime
validation also checks self-consistent content hashes and canonical outer-set
ordering, which JSON Schema alone does not express. This is a local structural
gate: it checks declared eligibility but does not dereference predecessor
receipts or establish adjudication correctness.

The available refresh did not contain the seven standalone input files and
expected-output manifest described by the current manuscript. Its controls are
constructed inline by `reproduce.py` and `tests/test_enforcement.py`; the
top-level claim map therefore grades that part of the manuscript claim as
partial rather than treating these controls as the missing seven-file set.
