"""
PATCH-011 V1 acceptance compatibility layer.

The canonical PATCH-011 executor is now implemented in
patch_011_execution.py.  V1 acceptance tests are retained as
historical coverage, but delegate to the canonical implementation
rather than maintaining a second executor.
"""

from patch_011_execution import execute_patch_plan

__all__ = ["execute_patch_plan"]
