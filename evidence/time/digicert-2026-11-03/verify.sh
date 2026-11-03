#!/usr/bin/env bash
# Verifies the RFC 3161 time-stamp tokens of this directory, offline, and that each stamp lies inside the validity of the CIC certificates that signed the records.
#
#   verify.sh            run from a clone of cic-primitives that holds the three release commits (git history); exit 0 only if every check holds
#   verify.sh --selftest the same, and then the NEGATIVE controls, which must FAIL; if one of them passes, this script fails
#
# THE TIME. The time of a stamp is read from the TOKEN (the signed genTime), never from manifest.json; the manifest value is only compared with it. EVERY token check runs
# at that time (-attime), so a later end of the TSA chain does not change the result, and the check does not depend on the clock of the machine.
#
# Per release it checks: (1) the record, read from git at its release commit, has the SHA-256 the manifest names; (2) the token answers our request, covers the record file,
# and chains to the self-signed DigiCert root kept in trust-anchor/, all three AT genTime; (3) the CIC certificates kept in cic-chain/ are the ones the record carries
# (developer, Source CA, root), the Developer CA that the record does NOT carry really issues the developer certificate, and genTime lies inside the validity window of
# EACH of the four (not before, not after), checked twice: openssl verify -attime over both chains, and plain arithmetic on the dates.
# Needs openssl, git, python3 with PyYAML (to read the certificates out of the record). No network.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
M="$HERE/manifest.json"
ANCHOR="$HERE/trust-anchor/DigiCert_Trusted_Root_G4.pem"
C="$HERE/cic-chain"
fail=0
say() { printf '%s\n' "$*"; }
bad() { say "FAIL  $*"; fail=1; }
ok()  { say "ok    $*"; }
mj() { python3 -c 'import json,sys;o=json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."): o=o[int(k)] if isinstance(o,list) else o[k]
print(o)' "$M" "$1"; }
fp() { openssl x509 -in "$1" -noout -fingerprint -sha256 | cut -d= -f2; }
epoch() { date -u -d "$1" +%s; }
notbefore() { epoch "$(openssl x509 -in "$1" -noout -startdate | cut -d= -f2)"; }
notafter()  { epoch "$(openssl x509 -in "$1" -noout -enddate | cut -d= -f2)"; }

# the four CIC certificates must lie around a time: plain arithmetic, fail closed. Prints nothing; returns 0 only if EVERY one holds at $1 (epoch).
cic_window_ok() {
  local t=$1 f
  for f in developer.pem developer-ca.pem source-ca.pem root.pem; do
    [ "$(notbefore "$C/$f")" -le "$t" ] && [ "$t" -le "$(notafter "$C/$f")" ] || return 1
  done
}
# the same time, by openssl over the two chains the records use (developer <- Developer CA <- root, and Source CA <- root)
cic_chains_ok() {
  local t=$1
  openssl verify -attime "$t" -CAfile "$C/root.pem" -untrusted "$C/developer-ca.pem" "$C/developer.pem" >/dev/null 2>&1 &&
  openssl verify -attime "$t" -CAfile "$C/root.pem" "$C/source-ca.pem" >/dev/null 2>&1
}

# ---- the anchors and the kept certificates are the ones the manifest names
want256=$(mj trust_anchor.sha256); want1=$(mj trust_anchor.sha1)
[ "$(fp "$ANCHOR")" = "$want256" ] && [ "$(openssl x509 -in "$ANCHOR" -noout -fingerprint -sha1 | cut -d= -f2)" = "$want1" ] && ok "TSA trust anchor $want256" || bad "TSA trust anchor differs from the manifest"
for name in developer developer-ca source-ca root; do
  want=$(mj "cic_chain.$name.sha256"); got=$(fp "$C/$name.pem")
  [ "$got" = "$want" ] && ok "CIC certificate $name $got" || bad "CIC certificate $name differs from the manifest ($got)"
done

n=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["stamps"]))' "$M")
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
for i in $(seq 0 $((n - 1))); do
  rel=$(mj "stamps.$i.release"); commit=$(mj "stamps.$i.record.git_commit"); path=$(mj "stamps.$i.record.path"); rsha=$(mj "stamps.$i.record.sha256")
  tsr="$HERE/$(mj "stamps.$i.response.file")"; tsq="$HERE/$(mj "stamps.$i.request.file")"; manifest_time=$(mj "stamps.$i.response.stamp_time_utc")
  if ! git cat-file -e "$commit^{commit}" 2>/dev/null; then bad "$rel: the commit $commit is not in this clone (fetch the full history)"; continue; fi
  git show "$commit:$path" > "$tmp/rec-$rel.yaml" 2>/dev/null
  [ "$(sha256sum "$tmp/rec-$rel.yaml" | cut -d' ' -f1)" = "$rsha" ] && ok "$rel: the record at ${commit:0:8} has sha256 ${rsha:0:16}..." || { bad "$rel: the record at $commit is not the one in the manifest"; continue; }

  # the time, from the token
  token_time=$(openssl ts -reply -in "$tsr" -text 2>/dev/null | sed -n 's/^Time stamp: //p')
  if [ -z "$token_time" ]; then bad "$rel: no time stamp could be read from the token"; continue; fi
  at=$(epoch "$token_time")
  [ "$token_time" = "$manifest_time" ] && ok "$rel: the time in the token ($token_time) equals the manifest" || bad "$rel: the time in the token ($token_time) is not the manifest's ($manifest_time)"

  # the token, ALL checks at the stamp time
  openssl ts -verify -queryfile "$tsq" -in "$tsr" -CAfile "$ANCHOR" -attime "$at" >/dev/null 2>&1 && ok "$rel: the token answers our request (digest and nonce) and chains to the anchor, at $token_time" || bad "$rel: the token does not answer the request / does not chain to the anchor at the stamp time"
  openssl ts -verify -data "$tmp/rec-$rel.yaml" -in "$tsr" -CAfile "$ANCHOR" -attime "$at" >/dev/null 2>&1 && ok "$rel: the token covers the record file, at $token_time" || bad "$rel: the token does not cover the record file at the stamp time"

  # the CIC certificates: the kept ones are the record's own, the Developer CA is the issuer, and the stamp lies inside every window
  # compared as CERTIFICATES (the SHA-256 of the DER), not as text: the field of a record may be a plain PEM (v0.1.5) or the printed text of openssl x509 -text with the PEM
  # block at its end (v0.2.0, v0.2.1); a record is not changed for that, and the same certificate must be recognised in both
  python3 - "$tmp/rec-$rel.yaml" "$tmp" "$rel" <<'PY' || true
import sys, yaml
rec = yaml.safe_load(open(sys.argv[1], encoding="utf-8")); out, rel = sys.argv[2], sys.argv[3]
fields = {"developer": rec["release"]["createdBy"]["certificate"], "source-ca": rec["cic_countersign"]["authority"]["certificate"], "root": rec["cic_countersign"]["authority"]["root_certificate"]}
for k, v in fields.items():
    i = v.find("-----BEGIN CERTIFICATE-----")
    open("%s/%s-%s.pem" % (out, rel, k), "w", encoding="utf-8").write(v[i:] if i >= 0 else "")
PY
  diffs=""
  for k in developer source-ca root; do
    r="$tmp/$rel-$k.pem"
    if [ -s "$r" ] && [ "$(fp "$r" 2>/dev/null)" = "$(fp "$C/$k.pem")" ]; then :; else diffs="$diffs $k"; fi
  done
  [ -z "$diffs" ] && echo SAME > "$tmp/cmp-$rel.txt" || echo "DIFFERENT:$diffs" > "$tmp/cmp-$rel.txt"
  [ "$(cat "$tmp/cmp-$rel.txt")" = "SAME" ] && ok "$rel: developer, Source CA and root kept here are the same certificates as the record carries (by DER, not by text)" || bad "$rel: the certificates kept here are not the record's own ($(cat "$tmp/cmp-$rel.txt"))"
  cic_chains_ok "$at" && ok "$rel: openssl: both CIC chains are valid at the stamp time, the Developer CA being the issuer of the developer certificate" || bad "$rel: openssl: a CIC chain is NOT valid at the stamp time"
  if cic_window_ok "$at"; then
    ok "$rel: the stamp ($token_time) is inside the validity of the developer certificate, Developer CA, Source CA and root"
    for f in developer developer-ca source-ca root; do say "        margin before the end of $f.pem: $(( ($(notafter "$C/$f.pem") - at) / 86400 )) days"; done
  else bad "$rel: the stamp is OUTSIDE the validity of at least one CIC certificate"; fi

  if [ "${1:-}" = "--selftest" ]; then
    cp "$tmp/rec-$rel.yaml" "$tmp/alt-$rel.yaml"; printf '#' >> "$tmp/alt-$rel.yaml"
    if openssl ts -verify -data "$tmp/alt-$rel.yaml" -in "$tsr" -CAfile "$ANCHOR" -attime "$at" >/dev/null 2>&1; then bad "$rel: SELFTEST a record changed by one byte was ACCEPTED"; else ok "$rel: selftest, a record changed by one byte is refused"; fi
    if openssl ts -verify -data "$tmp/rec-$rel.yaml" -in "$tsr" -CAfile /usr/share/ca-certificates/mozilla/DigiCert_Global_Root_G2.crt -attime "$at" >/dev/null 2>&1; then bad "$rel: SELFTEST a wrong anchor was ACCEPTED"; else ok "$rel: selftest, a wrong anchor is refused"; fi
    after=$(epoch "2027-01-15"); before=$(epoch "2026-03-01")
    if cic_window_ok "$after" || cic_chains_ok "$after"; then bad "$rel: SELFTEST a stamp in 2027, after the CIC chain ended, was ACCEPTED"; else ok "$rel: selftest, a stamp after the end of the CIC chain is refused (both ways)"; fi
    if cic_window_ok "$before" || cic_chains_ok "$before"; then bad "$rel: SELFTEST a stamp before the CIC chain began was ACCEPTED"; else ok "$rel: selftest, a stamp before the CIC chain began is refused (both ways)"; fi
    between=$(epoch "2026-12-31 13:22:50")      # after the Developer CA (13:22:46) and the Source CA (13:22:39) ended, before the developer certificate (13:22:59) did
    if cic_window_ok "$between" || cic_chains_ok "$between"; then bad "$rel: SELFTEST a stamp after ONE of the CIC certificates ended was ACCEPTED"; else ok "$rel: selftest, a stamp when only SOME CIC certificates are still valid is refused"; fi
  fi
done
if [ "${1:-}" = "--selftest" ]; then
  # the Developer CA that issues the developer certificate must be the real one: the Source CA in its place is refused
  if openssl verify -attime "$(epoch '2026-11-03 22:07:48')" -CAfile "$C/root.pem" -untrusted "$C/source-ca.pem" "$C/developer.pem" >/dev/null 2>&1; then bad "SELFTEST the Source CA was accepted as the issuer of the developer certificate"; else ok "selftest, a wrong issuer of the developer certificate is refused"; fi
fi
[ "$fail" = 0 ] && say "ALL CHECKS HOLD" || say "AT LEAST ONE CHECK FAILED"
exit "$fail"
