"""Crypto helpers shared by the test modules.

Both test files need an ephemeral key pair and a way to produce a
`vault:v1:...` signature over a pre-hashed digest. They had one copy each,
which is the same duplication problem this repository spends its effort
preventing in the schema layer.
"""

import base64
import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import utils as asym_utils
from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDSA,
    SECP256R1,
    generate_private_key,
)
from cryptography.x509.oid import NameOID


def make_test_key_and_cert(common_name="Test Dev"):
    """An ephemeral ECDSA P-256 key pair and self-signed certificate."""
    private_key = generate_private_key(SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .serial_number(x509.random_serial_number())
        .public_key(private_key.public_key())
        .sign(private_key, hashes.SHA256())
    )
    return private_key, cert.public_bytes(serialization.Encoding.PEM).decode()


def sign_hash(private_key, digest_b64):
    """Sign a pre-hashed digest, in the `vault:v1:<base64>` form Vault returns."""
    hash_bytes = base64.b64decode(digest_b64)
    sig_bytes = private_key.sign(hash_bytes, ECDSA(asym_utils.Prehashed(hashes.SHA256())))
    return "vault:v1:" + base64.b64encode(sig_bytes).decode()
