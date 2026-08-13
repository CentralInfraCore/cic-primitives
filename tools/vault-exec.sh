#!/usr/bin/env bash
#
# Run a command in the builder container with working Vault access.
#
# Three things go wrong between a host shell that can reach Vault and a
# container that cannot, and each one produces a misleading error:
#
# 1. The container never sees the credentials.
#    docker-compose.yml interpolates ${VAULT_ADDR} and ${VAULT_TOKEN} when the
#    container is CREATED. A builder started before the token was exported
#    captures empty strings for its whole life, and `make release` then reports
#    "VAULT_ADDR and VAULT_TOKEN must be set" while the caller's shell has both.
#    Passing them at exec time removes the dependency on who started it, when.
#
# 2. 127.0.0.1 means something else inside a container.
#    VAULT_ADDR=https://127.0.0.1:18200 is correct on the host and points at the
#    container's own loopback inside it — "Connection refused", with a traceback
#    that says nothing about namespaces. The compose file already provides
#    host.docker.internal; this rewrites the host part to use it.
#
# 3. TLS gets switched off for the wrong reason.
#    compiler.py reads VAULT_CACERT; the host convention here is
#    VAULT_CA_CERT_FILE, and the file lives under $XDG_RUNTIME_DIR, which is not
#    mounted. So verification silently degraded to "disabled" even though the
#    server certificate lists host.docker.internal in its SAN and verification
#    would succeed. The CA is copied into the mounted tree and pointed at.
#
# Usage: tools/vault-exec.sh <command> [args...]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -z "${VAULT_ADDR:-}" ] || [ -z "${VAULT_TOKEN:-}" ]; then
  echo "[!] VAULT_ADDR and VAULT_TOKEN must be set in this shell." >&2
  exit 1
fi

# The host address, as the container has to say it.
CONTAINER_ADDR="${VAULT_ADDR/127.0.0.1/host.docker.internal}"
CONTAINER_ADDR="${CONTAINER_ADDR/localhost/host.docker.internal}"

# The CA, if the host has one. VAULT_CACERT is what compiler.py reads;
# VAULT_CA_CERT_FILE is what the host tooling sets. Accept either.
CA_SRC="${VAULT_CACERT:-${VAULT_CA_CERT_FILE:-}}"
CA_ARGS=()
CA_LOCAL=".vault-ca.crt"
if [ -n "$CA_SRC" ] && [ -f "$CA_SRC" ]; then
  cp "$CA_SRC" "$CA_LOCAL"
  chmod 600 "$CA_LOCAL"
  CA_ARGS=(-e "VAULT_CACERT=/app/$CA_LOCAL")
  trap 'rm -f "$REPO_ROOT/$CA_LOCAL"' EXIT
else
  echo "[!] No Vault CA certificate found (VAULT_CACERT / VAULT_CA_CERT_FILE)." >&2
  echo "    The request would fall back to an unverified TLS connection, which" >&2
  echo "    sends the signing token to whatever answers on $CONTAINER_ADDR." >&2
  echo "    Set one of those variables, or start Vault so its CA is written." >&2
  exit 1
fi

exec docker compose exec \
  -e "VAULT_ADDR=$CONTAINER_ADDR" \
  -e VAULT_TOKEN \
  "${CA_ARGS[@]}" \
  builder "$@"
