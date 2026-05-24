#!/usr/bin/env bash
# DEPRECATED: This script is no longer part of the release pipeline.
# Use: python tools/compiler.py release
# Output: release/<name>-vX.Y.Z.yaml (PrimitiveRelease bundle, Vault-signed)
echo "[FATAL] release.sh is deprecated. Run: python tools/compiler.py release" >&2
exit 1
