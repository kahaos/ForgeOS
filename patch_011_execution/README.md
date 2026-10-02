# PATCH-011 Execution Package

Files:
- PATCH-011_EXECUTION_SPEC.md
- local_test_handler.py
- apply_patch_011_execution.sh
- test_patch_011_execution.py

This package is deliberately split into a bounded handler and a fail-closed
installer. It must not introduce arbitrary command execution or production
deployment.
