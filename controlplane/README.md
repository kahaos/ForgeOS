# ForgeOS control plane

ForgeOS sits between AI agents and the systems they are allowed to touch.

`agent → gateway → policy → approval? → tool → evidence`

This package is the 1.0 cut. The numbered `PATCH-*` files in the repo root are the earlier laboratory and are not the product.

## Run

```bash
python -m controlplane.demo
```

The demo exercises allow, deny, human approval, and tamper-evident evidence-chain verification.