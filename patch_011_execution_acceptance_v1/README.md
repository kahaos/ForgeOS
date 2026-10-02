# PATCH-011 Controlled Execution Acceptance

This package is the next acceptance step after the v2 fail-closed foundation.

It adds a narrowly scoped execution engine and tests for:
- registered local-test handler
- READY -> EXECUTING -> VERIFYING -> COMPLETED
- evidence and receipt
- replay resistance
- production-target rejection

It does NOT enable production execution.
