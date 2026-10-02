# ForgeOS Alpha 0.8 — PATCH-012 / Freeze Package

Run `apply_patch_012_and_freeze.sh` from the ForgeOS product root.

The script:
- backs up the live execution module;
- fixes the evidence path binding (`artifact` -> evidence `path`);
- creates PLAN-000005 / PATCH-B;
- validates and executes it against `local-test`;
- verifies evidence and receipt integrity;
- verifies replay protection;
- creates the Alpha 0.8 freeze record and changelog;
- creates `forgeos_alpha_0_8_freeze_archive.zip`.

Review the resulting hashes and archive locally before uploading to Dropbox.
