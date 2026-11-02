"""Negative vectors for a value that ends in a newline (the follow-up to PR #25; docs/en/RELEASE-RECORD-CONTRACT.md sections 5 and 6).

The contract says a commit is 40 lowercase hexadecimal digits and a digest is `sha256:` followed by 64 lowercase hexadecimal digits. In Python an end anchor `$` also
matches in front of a final newline, so the first version of the verifier accepted `<40 hex>\\n` and `sha256:<64 hex>\\n`. These vectors are the proof of that defect (they
fail against the verifier of d2d8ec7) and the guard of its fix. They are kept apart from tests/e3_vectors.py, which is frozen (tests/fixtures/envelope3/FROZEN.sha256).

The same defects are applied to the golden record and re-authenticated, like every vector of e3_vectors.py, so the refusal has to come from the contract check.
"""
from e3_vectors import FIX, s, v

COMMIT = "f0cf873c0e2f889d440cc7411535a63a89a41e9f"            # the commit of the worked example
FILE_DIGEST = "sha256:b6a98d9ce9a2d9149288fa3df42d377c3e42737afdcdaf714e33c0a100b51060"       # artifacts.files.0.digest of the golden record
MANIFEST_DIGEST = "sha256:39e022575a650d2c2cf04a4d65ae8744e04d0ccb3699fb417db9c4c160b2ec53"   # artifacts.manifest_digest of the golden record

# the three forms the contract states, each followed by a final newline
NEWLINE = [
    v("source-commit-trailing-newline", "record", "source_commit_form", [s("provenance.source_commit", COMMIT + "\n")]),
    v("digest-trailing-newline", "record", "artifact_digest_form", [s("artifacts.files.0.digest", FILE_DIGEST + "\n"), FIX]),
    v("manifest-digest-trailing-newline", "record", "artifact_manifest_digest_form", [s("artifacts.manifest_digest", MANIFEST_DIGEST + "\n")]),
]

# controls: they are refused before and after the fix, so they show the boundary of the defect and not a new refusal
CONTROLS = [
    v("source-commit-two-trailing-newlines", "record", "source_commit_form", [s("provenance.source_commit", COMMIT + "\n\n")]),
    v("digest-trailing-carriage-return", "record", "artifact_digest_form", [s("artifacts.files.0.digest", FILE_DIGEST + "\r"), FIX]),
    v("digest-leading-newline", "record", "artifact_digest_form", [s("artifacts.files.0.digest", "\n" + FILE_DIGEST), FIX]),
    v("manifest-digest-trailing-space", "record", "artifact_manifest_digest_form", [s("artifacts.manifest_digest", MANIFEST_DIGEST + " ")]),
]

ALL = NEWLINE + CONTROLS
