#!/usr/bin/env python3
"""Main-call execution boundary guarded by a recomputed PROCEED receipt."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import subprocess
import sys
from typing import Any, TypeVar

from .adequacy import EnforcementError, ErrorCode, load_receipt, verify_proceed_receipt


T = TypeVar("T")


def run_main_call(
    *,
    content_run_id: str,
    unit_receipt_set: Any,
    proceed_receipt: Any,
    call: Callable[[], T],
) -> T:
    """Invoke *call* only after the exact receipt binding recomputes PROCEED."""

    # This check is intentionally the first operation at the call boundary.
    # In particular, no client construction, network access, or callback runs
    # before a valid decision has been recomputed from receipt_set<U_A>.
    verify_proceed_receipt(
        proceed_receipt,
        unit_receipt_set,
        content_run_id=content_run_id,
    )
    if not callable(call):
        raise EnforcementError(
            ErrorCode.PROCEED_RECEIPT_INVALID,
            "authorized main-call target is not callable",
        )
    return call()


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a command only after a valid PROCEED receipt is recomputed "
            "against its U_A receipt set."
        )
    )
    parser.add_argument("--unit-receipts")
    parser.add_argument("--proceed-receipt")
    parser.add_argument("--content-run-id")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)

    try:
        proceed = (
            None
            if arguments.proceed_receipt is None
            else load_receipt(arguments.proceed_receipt)
        )
        units = (
            None
            if arguments.unit_receipts is None
            else load_receipt(arguments.unit_receipts)
        )

        def invoke() -> int:
            if not arguments.command:
                raise EnforcementError(
                    ErrorCode.PROCEED_RECEIPT_INVALID,
                    "no main-call command was supplied",
                )
            completed = subprocess.run(arguments.command, check=False)
            return completed.returncode

        return run_main_call(
            content_run_id=arguments.content_run_id,
            unit_receipt_set=units,
            proceed_receipt=proceed,
            call=invoke,
        )
    except EnforcementError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
