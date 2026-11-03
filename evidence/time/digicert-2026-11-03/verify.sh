#!/usr/bin/env bash
# Verifies the RFC 3161 time-stamp tokens of this directory, offline, against the self-signed DigiCert Trusted Root G4 kept in trust-anchor/.
#
#   verify.sh            run from a clone of cic-primitives that holds the three release commits (git history); exit 0 only if every check holds
#   verify.sh --selftest the same, and then the NEGATIVE controls: a record changed by one byte and a wrong anchor must FAIL; if one of them passes, this script fails
#
# What it checks, for each of the three releases: (1) the anchor is the one whose figures are written in manifest.json; (2) the record, read from git at its release
# commit, has the SHA-256 the manifest names; (3) the token is valid for that record, chained to the anchor, and its time stamp lies inside the validity of every
# certificate (openssl ts -verify -attime <the time stamp>). Needs openssl, git, python3 (json only). No network.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
M="$HERE/manifest.json"
ANCHOR="$HERE/trust-anchor/DigiCert_Trusted_Root_G4.pem"
fail=0
say() { printf '%s\n' "$*"; }
bad() { say "FAIL  $*"; fail=1; }
ok()  { say "ok    $*"; }

want256=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["trust_anchor"]["sha256"])' "$M")
want1=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["trust_anchor"]["sha1"])' "$M")
got256=$(openssl x509 -in "$ANCHOR" -noout -fingerprint -sha256 | cut -d= -f2)
got1=$(openssl x509 -in "$ANCHOR" -noout -fingerprint -sha1 | cut -d= -f2)
[ "$got256" = "$want256" ] && [ "$got1" = "$want1" ] && ok "trust anchor $got256" || bad "trust anchor differs from the manifest ($got256)"

n=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["stamps"]))' "$M")
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
for i in $(seq 0 $((n - 1))); do
  f() { python3 -c 'import json,sys;d=json.load(open(sys.argv[1]))["stamps"][int(sys.argv[2])];o=d
for k in sys.argv[3].split("."): o=o[k]
print(o)' "$M" "$i" "$1"; }
  rel=$(f release); commit=$(f record.git_commit); path=$(f record.path); rsha=$(f record.sha256)
  tsr="$HERE/$(f response.file)"; tsq="$HERE/$(f request.file)"; stamp=$(f response.stamp_time_utc)
  if ! git cat-file -e "$commit^{commit}" 2>/dev/null; then bad "$rel: the commit $commit is not in this clone (fetch the full history)"; continue; fi
  git show "$commit:$path" > "$tmp/rec-$rel.yaml" 2>/dev/null
  [ "$(sha256sum "$tmp/rec-$rel.yaml" | cut -d' ' -f1)" = "$rsha" ] && ok "$rel: the record at $commit has sha256 ${rsha:0:16}..." || { bad "$rel: the record at $commit is not the one in the manifest"; continue; }
  at=$(date -u -d "$stamp" +%s)
  openssl ts -verify -queryfile "$tsq" -in "$tsr" -CAfile "$ANCHOR" >/dev/null 2>&1 && ok "$rel: the token answers our request (digest and nonce) and chains to the anchor" || bad "$rel: the token does not answer the request / does not chain to the anchor"
  openssl ts -verify -data "$tmp/rec-$rel.yaml" -in "$tsr" -CAfile "$ANCHOR" >/dev/null 2>&1 && ok "$rel: the token covers the record file" || bad "$rel: the token does not cover the record file"
  openssl ts -verify -data "$tmp/rec-$rel.yaml" -in "$tsr" -CAfile "$ANCHOR" -attime "$at" >/dev/null 2>&1 && ok "$rel: valid at the time stamp ($stamp)" || bad "$rel: not valid at the time stamp"
  if [ "${1:-}" = "--selftest" ]; then
    cp "$tmp/rec-$rel.yaml" "$tmp/alt-$rel.yaml"; printf '#' >> "$tmp/alt-$rel.yaml"
    if openssl ts -verify -data "$tmp/alt-$rel.yaml" -in "$tsr" -CAfile "$ANCHOR" >/dev/null 2>&1; then bad "$rel: SELFTEST a record changed by one byte was ACCEPTED"; else ok "$rel: selftest, a record changed by one byte is refused"; fi
    if openssl ts -verify -data "$tmp/rec-$rel.yaml" -in "$tsr" -CAfile /usr/share/ca-certificates/mozilla/DigiCert_Global_Root_G2.crt >/dev/null 2>&1; then bad "$rel: SELFTEST a wrong anchor was ACCEPTED"; else ok "$rel: selftest, a wrong anchor is refused"; fi
  fi
done
[ "$fail" = 0 ] && say "ALL CHECKS HOLD" || say "AT LEAST ONE CHECK FAILED"
exit "$fail"
