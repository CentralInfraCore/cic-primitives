import os
import sys
import glob
import yaml
import json
import hashlib
import requests
import subprocess
import datetime
import re
from jsonschema import validate
import base64
import semver

# --- Configuration Loader ---

def load_project_config(full_config=False):
    """Loads the main project.yaml configuration file."""
    try:
        with open('project.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config if full_config else config['compiler_settings']
    except (IOError, KeyError, TypeError) as e:
        print(f"[FATAL] Could not load or parse compiler settings from project.yaml: {e}")
        sys.exit(1)

CONFIG = load_project_config()

# --- Helper Functions ---


def load_yaml(path):
    """Loads a YAML file."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def write_yaml(path, data):
    """Writes data to a YAML file."""
    with open(path, 'w') as f:
        yaml.dump(data, f, sort_keys=False, indent=2)


def to_canonical_json(data):
    """Converts a Python object to a canonical (sorted, no whitespace)
    JSON string."""
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode(
        'utf-8')


def get_sha256_hex(data_bytes):
    """Calculates the SHA256 hash and returns it as a hex digest."""
    return hashlib.sha256(data_bytes).hexdigest()


def get_sha256_b64(data_bytes):
    """Calculates the SHA256 hash and returns it as a base64 encoded string."""
    return base64.b64encode(hashlib.sha256(data_bytes).digest()).decode('utf-8')


DEV_VERSION_RE = re.compile(r'^v\d+\.\d+(\.\d+)?\.dev$')


def _inject_version(obj, version_str):
    """Recursively replaces any dev placeholder version with the release version.

    Matched by pattern, not against the literal 'v0.0.dev'. The literal check
    became silently wrong the moment an atom moved off v0.0: shape.yaml and
    role.yaml are v0.1.dev, and a literal comparison would have carried '.dev'
    into a signed release bundle while every other file carried the real
    version. Any vX.Y[.Z].dev is a placeholder.
    """
    if isinstance(obj, dict):
        return {k: _inject_version(v, version_str) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_inject_version(item, version_str) for item in obj]
    if isinstance(obj, str) and DEV_VERSION_RE.match(obj):
        return version_str
    return obj


RELEASE_ENVELOPE_VERSION = 2


def _release_hash_payload(bundle, envelope_version):
    """What build_hash covers, per envelope version.

    v1 — {createdBy, releasedBy, specs, validity}. Everything else in the
         bundle was unsigned: kind, version and timestamp could be rewritten
         at will and verification still succeeded. Demonstrated: a bundle
         relabelled 0.1.5 -> 9.9.9 with a 2099 timestamp verified clean.

    v2 — the WHOLE bundle except the two members that cannot be inside their
         own signature: release.sign, and the counter-signature block that is
         applied afterwards by a different authority. Enumerating fields is
         how v1 went wrong; excluding two and covering the rest cannot leave
         a new field accidentally unsigned.

    v1 stays supported because release/cic-primitives-v0.1.5.yaml was signed
    under it and must keep verifying. New releases are written as v2.
    """
    if envelope_version == 1:
        return {
            'createdBy': bundle.get('createdBy'),
            'releasedBy': bundle.get('release', {}).get('createdBy'),
            'specs': bundle.get('specs'),
            'validity': bundle.get('validity'),
        }
    if envelope_version == 2:
        payload = json.loads(json.dumps(bundle, sort_keys=True, default=str))
        payload.pop('cic_countersign', None)
        release_block = payload.get('release')
        if isinstance(release_block, dict):
            release_block.pop('sign', None)
            release_block.pop('build_hash', None)
        return payload
    return None


def _collect_provenance():
    """Facts about WHERE this build came from, so the signature can cover them."""
    provenance = {'envelope': RELEASE_ENVELOPE_VERSION}
    try:
        provenance['source_commit'] = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], capture_output=True, text=True,
            check=True).stdout.strip()
    except Exception:
        provenance['source_commit'] = None
    for label, path in (('dependency_lock', 'dependency.yaml'),
                        ('grammar', 'proposals/atom-grammar/check_grammar.py'),
                        ('grammar_schema', 'proposals/atom-grammar/instance-grammar.schema.yaml')):
        try:
            with open(path, 'rb') as fh:
                provenance[f'{label}_sha256'] = get_sha256_b64(fh.read())
        except OSError:
            provenance[f'{label}_sha256'] = None
    return provenance


def get_reproducible_repo_hash(tree_id):
    """
    Calculates a reproducible SHA256 hash of a given git tree object.
    It creates a normalized tar archive in memory and hashes its content,
    ensuring the hash is independent of file metadata like permissions or
    timestamps. The result is base64 encoded.
    """
    # Create a tar archive from the tree object
    archive_proc = subprocess.Popen(
        ['git', 'archive', '--format=tar', tree_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    digest_proc = subprocess.Popen(
        ['openssl', 'dgst', '-sha256', '-binary'],
        stdin=archive_proc.stdout,
        stdout=subprocess.PIPE
    )
    b64_proc = subprocess.Popen(
        ['openssl', 'base64', '-A'],
        stdin=digest_proc.stdout,
        stdout=subprocess.PIPE,
        text=True
    )
    archive_proc.stdout.close()

    repo_hash_b64 = b64_proc.communicate()[0].strip()
    archive_proc.wait()
    digest_proc.wait()

    if archive_proc.returncode != 0:
        print("\033[91m✗ ERROR: git archive failed.\033[0m")
        sys.exit(1)
    if digest_proc.returncode != 0:
        print("\033[91m✗ ERROR: openssl dgst failed.\033[0m")
        sys.exit(1)
    if b64_proc.returncode != 0:
        print("\033[91m✗ ERROR: Failed to calculate reproducible repository hash.\033[0m")
        sys.exit(1)

    return repo_hash_b64


def run_git_command(command):
    """Runs a Git command and returns its output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"\033[91m✗ ERROR: Git command failed: {' '.join(command)}\033[0m")
        print(e.stderr)
        sys.exit(1)


def validate_release_prerequisites():
    """
    Ensures that all conditions for a release are met:
    1. Clean git state.
    2. Correct release branch name format.
    3. New version is the next logical increment (no gaps).
    """
    print("--- Validating Release Prerequisites ---")
    project_config = load_project_config(full_config=True)['project']

    raw_component_name = project_config.get('main_branch', 'main')
    component_name = re.sub(r'main$', '', raw_component_name)

    # 1. Check for clean git state
    git_status = run_git_command(['git', 'status', '--porcelain'])
    if git_status:
        print("\033[91m✗ ERROR: Uncommitted changes detected. Please commit or stash them before releasing.\033[0m")
        sys.exit(1)
    print("  \033[92m✓ Git working directory is clean.\033[0m")

    # 2. Validate branch name and extract version
    current_branch = run_git_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    release_branch_pattern = re.compile(rf"^{re.escape(component_name)}releases/v(\d+\.\d+\.\d+)$")
    match = release_branch_pattern.match(current_branch)

    if not match:
        print(f"\033[91m✗ ERROR: You are not on a valid release branch for the '{component_name}' component.\033[0m")
        print(f"  Expected format: '{component_name}releases/vX.Y.Z'")
        print(f"  Current branch: '{current_branch}'")
        sys.exit(1)

    new_version_str = match.group(1)
    new_version = semver.Version.parse(new_version_str)
    print(f"  \033[92m✓ Valid release branch found: {current_branch} (Version: {new_version_str})\033[0m")

    # 3. Check for strict +1 version increment (no gaps)
    tag_pattern = f"{component_name}@v*.*.*"
    git_tags_raw = run_git_command(['git', 'tag', '--list', tag_pattern])
    existing_tags = git_tags_raw.split('\n') if git_tags_raw else []

    if not existing_tags:
        if new_version.major != 0 or new_version.minor != 0 or new_version.patch != 0:
            # Allowing 0.0.0 or 0.1.0 or 1.0.0 as first release
            pass
        print("  \033[92m✓ No previous tags found. Proceeding with first release.\033[0m")
    else:
        existing_versions = sorted([semver.Version.parse(tag.split('@v')[-1]) for tag in existing_tags])
        latest_version = existing_versions[-1]

        is_valid_next = False
        # Valid next patch? (e.g., 1.2.5 -> 1.2.6)
        if new_version == latest_version.bump_patch():
            is_valid_next = True
        # Valid next minor? (e.g., 1.2.5 -> 1.3.0)
        elif new_version == latest_version.bump_minor() and new_version.patch == 0:
            is_valid_next = True
        # Valid next major? (e.g., 1.2.5 -> 2.0.0)
        elif new_version == latest_version.bump_major() and new_version.minor == 0 and new_version.patch == 0:
            is_valid_next = True

        if not is_valid_next:
            print(f"\033[91m✗ ERROR: Version '{new_version_str}' is not a valid next increment.\033[0m")
            print(f"  The latest version is '{latest_version}'. Allowed next versions are:")
            print(f"  - Patch: '{latest_version.bump_patch()}'")
            print(f"  - Minor: '{latest_version.bump_minor()}'")
            print(f"  - Major: '{latest_version.bump_major()}'")
            sys.exit(1)

    print(f"  \033[92m✓ New version '{new_version_str}' is a valid increment.\033[0m")

    return new_version_str, component_name


def run_validation():
    """Runs offline validation on all schemas."""
    print("--- Running Schema Validation ---")
    try:
        meta_schema = load_yaml(CONFIG['meta_schema_file'])
        print(f"Meta-schema loaded from {CONFIG['meta_schema_file']}")
    except Exception as e:
        print(f"[FATAL] Could not load meta-schema: {e}")
        sys.exit(1)

    schema_files = glob.glob(
        os.path.join(CONFIG['meta_schemas_dir'], '**', '*.meta.yaml'),
        recursive=True
    )
    # Exclude the meta-schema itself from validation
    schema_files = [f for f in schema_files if f != CONFIG.get('meta_schema_file')]

    all_valid = True
    for schema_file in schema_files:
        print(f"  Validating {schema_file}...")
        try:
            schema_instance = load_yaml(schema_file)
            validate(instance=schema_instance, schema=meta_schema)
            print("  \033[92m✓ OK\033[0m")
        except Exception as e:
            print(f"  \033[91m✗ ERROR: {e}\033[0m")
            all_valid = False

    if not all_valid:
        print("\nValidation failed for one or more schemas.")
        sys.exit(1)
    else:
        print("\nAll schemas are valid.")


def _vault_sign(content_hash_b64, vault_addr, vault_token, key_name, verify_tls):
    """Signs a pre-hashed digest via Vault Transit. Returns the signature string."""
    headers = {'X-Vault-Token': vault_token}
    payload = {'input': content_hash_b64, 'prehashed': True}
    resp = requests.post(
        f"{vault_addr}/v1/transit/sign/{key_name}",
        json=payload, headers=headers, verify=verify_tls
    )
    if resp.status_code != 200:
        print(f"\033[91m✗ ERROR: Vault sign failed ({resp.status_code}): {resp.text}\033[0m")
        sys.exit(1)
    return resp.json()['data']['signature']


def _vault_get_cert(vault_addr, vault_token, cert_path, verify_tls):
    """Reads a PEM cert from Vault KV v2. cert_path format: 'mount/secret-name/key'."""
    parts = cert_path.split('/', 2)
    if len(parts) != 3:
        print("\033[91m✗ ERROR: VAULT_CERT_PATH must be 'mount/secret-name/key'.\033[0m")
        sys.exit(1)
    mount, secret, key = parts
    headers = {'X-Vault-Token': vault_token}
    resp = requests.get(
        f"{vault_addr}/v1/{mount}/data/{secret}",
        headers=headers, verify=verify_tls
    )
    if resp.status_code != 200:
        print(f"\033[91m✗ ERROR: Vault cert fetch failed ({resp.status_code}): {resp.text}\033[0m")
        sys.exit(1)
    return resp.json()['data']['data'][key]


def _verify_cert_signature(cert_pem, vault_signature, content_hash_b64):
    """Verifies a Vault Transit ECDSA signature against a PEM certificate's public key.

    vault_signature format: "vault:v1:<base64-DER>"
    content_hash_b64: base64-encoded SHA256 digest (the pre-hashed input to Vault Transit)

    Returns (ok: bool, reason: str)
    """
    try:
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
        from cryptography.hazmat.primitives.asymmetric import utils as asym_utils
        from cryptography.hazmat.primitives import hashes
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        return False, "cryptography library not available (pip install cryptography)"

    try:
        cert = load_pem_x509_certificate(cert_pem.encode('utf-8'))
        public_key = cert.public_key()
    except Exception as e:
        return False, f"Certificate parse error: {e}"

    # Certificate temporal validity
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
    except AttributeError:
        # cryptography < 42 compat
        not_before = cert.not_valid_before.replace(tzinfo=datetime.timezone.utc)
        not_after = cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)

    if now < not_before or now > not_after:
        return False, f"Certificate not valid: {not_before.date()} → {not_after.date()}"

    # Extract DER signature bytes from Vault Transit format
    prefix = "vault:v1:"
    if not vault_signature.startswith(prefix):
        return False, f"Unexpected signature format (expected 'vault:v1:...'): {vault_signature[:24]}"
    try:
        sig_bytes = base64.b64decode(vault_signature[len(prefix):])
        hash_bytes = base64.b64decode(content_hash_b64)
    except Exception as e:
        return False, f"Base64 decode error: {e}"

    try:
        public_key.verify(sig_bytes, hash_bytes, ECDSA(asym_utils.Prehashed(hashes.SHA256())))
        return True, "OK"
    except InvalidSignature:
        return False, "Signature does not match certificate public key"
    except Exception as e:
        return False, f"Verification error: {e}"


def _verify_cert_chain(cert_pem, issuer_pem):
    """Verifies that `cert_pem` was issued by `issuer_pem`, and that both are in date.

    Returns (ok: bool, reason: str). This proves ISSUANCE, not trust: the issuer
    is whatever PEM it was handed. Pinning the issuer against an out-of-band
    trust anchor is the caller's job — see run_verify_release's --trust-root.
    """
    try:
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.hazmat.primitives.asymmetric.ec import ECDSA, EllipticCurvePublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        return False, "cryptography library not available"

    try:
        cert = load_pem_x509_certificate(cert_pem.encode('utf-8'))
        issuer = load_pem_x509_certificate(issuer_pem.encode('utf-8'))
    except Exception as e:
        return False, f"Certificate parse error: {e}"

    now = datetime.datetime.now(datetime.timezone.utc)
    for label, c in (("certificate", cert), ("root certificate", issuer)):
        not_before = getattr(c, 'not_valid_before_utc', None) or c.not_valid_before.replace(
            tzinfo=datetime.timezone.utc)
        not_after = getattr(c, 'not_valid_after_utc', None) or c.not_valid_after.replace(
            tzinfo=datetime.timezone.utc)
        if now < not_before:
            return False, f"{label} is not valid yet ({not_before.date()})"
        if now > not_after:
            return False, f"{label} expired on {not_after.date()}"

    if cert.issuer != issuer.subject:
        return False, (f"issuer mismatch: certificate says '{cert.issuer.rfc4514_string()}', "
                       f"root subject is '{issuer.subject.rfc4514_string()}'")

    try:
        pub = issuer.public_key()
        if isinstance(pub, EllipticCurvePublicKey):
            pub.verify(cert.signature, cert.tbs_certificate_bytes,
                       ECDSA(cert.signature_hash_algorithm))
        else:
            from cryptography.hazmat.primitives.asymmetric import padding
            pub.verify(cert.signature, cert.tbs_certificate_bytes,
                       padding.PKCS1v15(), cert.signature_hash_algorithm)
        return True, "OK"
    except InvalidSignature:
        return False, "certificate was not issued by this root"
    except Exception as e:
        return False, f"chain verification error: {e}"


def _cert_fingerprint(cert_pem):
    """SHA256 fingerprint of a PEM certificate, for pinning comparisons."""
    try:
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.hazmat.primitives import hashes as _h
        cert = load_pem_x509_certificate(cert_pem.encode('utf-8'))
        return base64.b64encode(cert.fingerprint(_h.SHA256())).decode()
    except Exception:
        return None


def _load_valid_commitment():
    """Loads commitment.yaml and verifies it is present and within its validity window."""
    if not os.path.isfile('commitment.yaml'):
        print("\033[91m✗ ERROR: commitment.yaml not found. Run 'make pledge' first.\033[0m")
        sys.exit(1)
    commitment = load_yaml('commitment.yaml')
    if commitment.get('kind') != 'DeveloperCommitment':
        print(f"\033[91m✗ ERROR: commitment.yaml has unexpected kind: {commitment.get('kind')}\033[0m")
        sys.exit(1)
    validity = commitment.get('validity', {})
    today = datetime.datetime.now(datetime.timezone.utc).date()
    valid_from = datetime.date.fromisoformat(validity.get('from', '1970-01-01'))
    valid_until = datetime.date.fromisoformat(validity.get('until', '1970-01-01'))
    if not (valid_from <= today <= valid_until):
        print(f"\033[91m✗ ERROR: Developer commitment is not valid today. Run 'make pledge' to renew.\033[0m")
        print(f"  valid_from: {valid_from}, valid_until: {valid_until}, today: {today}")
        sys.exit(1)
    print(f"  \033[92m✓ Developer commitment valid: {valid_from} → {valid_until}\033[0m")
    return commitment


def run_pledge():
    """Generates a signed developer commitment (validity + createdBy) to commitment.yaml.

    This is a pre-release step. The developer asserts responsibility for the project
    for the declared validity period, binding their X.509 certificate to the hash
    before Vault signs it.
    """
    print("--- Developer Pledge ---")

    vault_addr = os.getenv('VAULT_ADDR')
    vault_token = os.getenv('VAULT_TOKEN')
    vault_cacert = os.getenv('VAULT_CACERT')

    if not vault_addr or not vault_token:
        print("[FATAL] VAULT_ADDR and VAULT_TOKEN must be set.")
        sys.exit(1)

    verify_tls = vault_cacert if vault_cacert else False
    if not vault_cacert:
        print("\033[93m[WARNING] Vault TLS verification is disabled.\033[0m")

    full_config = load_project_config(full_config=True)
    project = full_config.get('project', {})
    settings = full_config.get('compiler_settings', {})

    vault_key = settings.get('vault_key_name', 'cic-my-sign-key')
    vault_cert_path = settings.get('vault_cert_path') or os.getenv('VAULT_CERT_PATH')
    owner_name = project.get('owner', '')
    owner_email = settings.get('owner_email') or next(
        (c['value'] for c in project.get('contacts', []) if c.get('type') == 'email'), ''
    )
    validity_days = int(settings.get('validity_days', 365))

    if not vault_cert_path:
        print("[FATAL] vault_cert_path must be set in project.yaml (compiler_settings) or VAULT_CERT_PATH env.")
        sys.exit(1)

    # 1. Fetch developer certificate from Vault KV
    print(f"  Fetching certificate from Vault ({vault_cert_path})...")
    cert_pem = _vault_get_cert(vault_addr, vault_token, vault_cert_path, verify_tls)
    print("  \033[92m✓ Certificate obtained.\033[0m")

    # 2. Build validity and createdBy blocks
    now = datetime.datetime.now(datetime.timezone.utc)
    valid_from = now.strftime('%Y-%m-%d')
    valid_until = (now + datetime.timedelta(days=validity_days)).strftime('%Y-%m-%d')

    validity = {'from': valid_from, 'until': valid_until}
    created_by = {
        'name': owner_name,
        'email': owner_email,
        'certificate': cert_pem,
    }

    # 3. Hash the pledge payload — certificate is inside the payload before signing
    pledge_payload = {'createdBy': created_by, 'validity': validity}
    content_hash = get_sha256_b64(to_canonical_json(pledge_payload))
    print(f"  Pledge hash: {content_hash[:24]}...")

    # 4. Sign via Vault Transit
    print(f"  Signing with Vault key '{vault_key}'...")
    signature = _vault_sign(content_hash, vault_addr, vault_token, vault_key, verify_tls)
    print("  \033[92m✓ Pledge signed.\033[0m")

    # 5. Write commitment.yaml
    commitment = {
        'kind': 'DeveloperCommitment',
        'created': now.isoformat(),
        'validity': validity,
        'createdBy': created_by,
        'pledge': {
            'content_hash': content_hash,
            'sign': signature,
        },
    }
    write_yaml('commitment.yaml', commitment)
    print(f"\n  \033[92m✓ commitment.yaml created.\033[0m")
    print(f"  Developer : {owner_name} <{owner_email}>")
    print(f"  Valid from: {valid_from}")
    print(f"  Valid until: {valid_until}")
    print(f"\n  \033[93mNext step: commit commitment.yaml, then run 'make release'.\033[0m")


def run_release():
    """Builds a signed PrimitiveRelease bundle artifact into release/."""
    print("--- Running Schema Release ---")
    release_version, component_name = validate_release_prerequisites()

    vault_addr = os.getenv('VAULT_ADDR')
    vault_token = os.getenv('VAULT_TOKEN')
    vault_cacert = os.getenv('VAULT_CACERT')

    if not vault_addr or not vault_token:
        print("[FATAL] VAULT_ADDR and VAULT_TOKEN must be set for release.")
        sys.exit(1)

    verify_tls = vault_cacert if vault_cacert else False
    if not vault_cacert:
        print("\033[93m[WARNING] Vault TLS verification is disabled. Do not use in production.\033[0m")

    # 1. Load and verify developer commitment (must exist and be within validity window)
    print("--- Verifying Developer Commitment ---")
    commitment = _load_valid_commitment()
    validity = commitment['validity']
    created_by = commitment['createdBy']

    # 2. Fetch release issuer certificate from Vault
    full_config = load_project_config(full_config=True)
    settings = full_config.get('compiler_settings', {})
    project = full_config.get('project', {})
    vault_key = settings.get('vault_key_name', 'cic-my-sign-key')
    vault_cert_path = settings.get('vault_cert_path') or os.getenv('VAULT_CERT_PATH')
    if not vault_cert_path:
        print("[FATAL] vault_cert_path must be set in project.yaml or VAULT_CERT_PATH env.")
        sys.exit(1)
    print(f"--- Fetching release issuer certificate ({vault_cert_path}) ---")
    release_cert_pem = _vault_get_cert(vault_addr, vault_token, vault_cert_path, verify_tls)
    print("  \033[92m✓ Release certificate obtained.\033[0m")
    release_owner_name = project.get('owner', '')
    release_owner_email = settings.get('owner_email') or next(
        (c['value'] for c in project.get('contacts', []) if c.get('type') == 'email'), ''
    )
    release_created_by = {
        'name': release_owner_name,
        'email': release_owner_email,
        'certificate': release_cert_pem,
    }

    # 3. Validate everything before building the artifact
    run_validation()
    run_primitive_validation()
    run_domain_compatibility_check()

    # 4. Collect schema files: atomic + aggregate, no examples, no index
    source_dir = CONFIG.get('source_dir', 'schemas')
    all_files = glob.glob(os.path.join(source_dir, '**', '*.yaml'), recursive=True)
    schema_files = sorted([
        f for f in all_files
        if os.path.basename(f) != 'index.yaml'
        and not f.endswith('.gitkeep')
        and '/examples/' not in f.replace(os.sep, '/')
        and os.path.getsize(f) > 0
    ])

    print(f"--- Building release bundle ({len(schema_files)} schemas) ---")

    # 5. Build specs[] — meta_hash over raw file bytes, version placeholder injected in spec content
    specs = []
    release_version_str = f"v{release_version}"
    for schema_file in schema_files:
        with open(schema_file, 'rb') as fh:
            raw = fh.read()
        meta_hash = get_sha256_b64(raw)
        spec_data = _inject_version(yaml.safe_load(raw), release_version_str)
        specs.append({
            'id': os.path.splitext(os.path.basename(schema_file))[0],
            'source_path': schema_file.replace(os.sep, '/'),
            'meta_hash': meta_hash,
            'spec': spec_data,
        })
        print(f"  - {schema_file}: {meta_hash[:16]}...")

    # 6. Build hash: {createdBy (developer), release.createdBy (issuer), specs, validity}
    #    Both certificates are cryptographically bound before Vault signs.
    #    Future: this will become a Merkle tree root over CI artifact layers.
    # 6b. Assemble the bundle FIRST, then hash it: under envelope v2 the
    #     signature covers the whole artifact, so the artifact has to exist
    #     before the hash can be taken.
    project_name = full_config.get('project', {}).get('name', 'XXprimitivesXX')
    bundle = {
        'kind': 'PrimitiveRelease',
        'version': release_version,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'validity': validity,
        'createdBy': created_by,
        'specs': specs,
        'provenance': _collect_provenance(),
        'release': {
            'envelope': RELEASE_ENVELOPE_VERSION,
            'createdBy': release_created_by,
        },
    }
    hash_payload = _release_hash_payload(bundle, RELEASE_ENVELOPE_VERSION)
    build_hash = get_sha256_b64(to_canonical_json(hash_payload))
    print(f"  - Build hash (envelope v{RELEASE_ENVELOPE_VERSION}): {build_hash[:16]}...")

    # 7. Sign via Vault Transit (one call for the entire bundle)
    print(f"  - Signing with Vault key '{vault_key}'...")
    signature = _vault_sign(build_hash, vault_addr, vault_token, vault_key, verify_tls)
    print("  \033[92m✓ Vault signature obtained.\033[0m")

    # 8. Write the bundle artifact
    bundle['release']['build_hash'] = build_hash
    bundle['release']['sign'] = signature

    os.makedirs('release', exist_ok=True)
    artifact_path = os.path.join('release', f"{project_name}-v{release_version}.yaml")
    write_yaml(artifact_path, bundle)
    print(f"\n  \033[92m✓ Release artifact: {artifact_path}\033[0m")
    print(f"  \033[93mACTION REQUIRED: git add {artifact_path} && git commit -m 'release: {release_version}' && git tag {component_name}@v{release_version}\033[0m")


def run_primitive_validation():
    """Validates all primitive YAML files in schemas/ against schemas/index.yaml."""
    primitive_schema_file = CONFIG.get('primitive_schema_file')
    if not primitive_schema_file:
        return
    print("--- Validating primitive schemas ---")
    try:
        index = load_yaml(primitive_schema_file)
        primitive_meta_schema = index['spec']
        print(f"Primitive meta-schema loaded from {primitive_schema_file}")
    except Exception as e:
        print(f"[FATAL] Could not load primitive meta-schema: {e}")
        sys.exit(1)

    source_dir = CONFIG.get('source_dir', 'schemas')
    schema_files = glob.glob(
        os.path.join(source_dir, '**', '*.yaml'),
        recursive=True
    )
    schema_files = [
        f for f in schema_files
        if not os.path.basename(f) == 'index.yaml'
        and not f.endswith('.gitkeep')
        and os.path.join('examples', 'invalid') not in f.replace(os.sep, '/')
        and os.path.getsize(f) > 0
    ]

    all_valid = True
    for schema_file in sorted(schema_files):
        print(f"  Validating {schema_file}...")
        try:
            instance = load_yaml(schema_file)
            if instance is None:
                continue
            validate(instance=instance, schema=primitive_meta_schema)
            print("  \033[92m✓ OK\033[0m")
        except Exception as e:
            print(f"  \033[91m✗ ERROR in {schema_file}: {e}\033[0m")
            all_valid = False

    if not all_valid:
        print("\nPrimitive validation failed.")
        sys.exit(1)
    else:
        print(f"\nAll {len(schema_files)} primitive schemas are valid.")


def run_domain_compatibility_check():
    """Phase 6.3: Verify DomainComposition slot compatibility with base aggregate.

    sealed  → must NOT be defined in DomainComposition
    required → MUST be defined in DomainComposition
    defaulted → may be defined (no type enforcement yet — D-008)
    """
    primitive_schema_file = CONFIG.get('primitive_schema_file')
    if not primitive_schema_file:
        return

    source_dir = CONFIG.get('source_dir', 'schemas')
    all_files = glob.glob(os.path.join(source_dir, '**', '*.yaml'), recursive=True)

    domain_files = []
    for f in all_files:
        if os.path.basename(f) == 'index.yaml' or f.endswith('.gitkeep'):
            continue
        if os.path.join('examples', 'invalid') in f.replace(os.sep, '/'):
            continue
        try:
            data = load_yaml(f)
            if data and data.get('spec', {}).get('kind') == 'DomainComposition':
                domain_files.append(f)
        except Exception:
            pass

    if not domain_files:
        return

    print("--- Checking DomainComposition compatibility ---")
    all_valid = True

    for domain_file in sorted(domain_files):
        print(f"  Checking {domain_file}...")
        try:
            domain = load_yaml(domain_file)
            spec = domain.get('spec', {})
            base_ref = spec.get('base', {}).get('ref')

            if not base_ref:
                print(f"  \033[93m⚠ WARNING: no base.ref, skipping\033[0m")
                continue

            base = load_yaml(base_ref)
            base_slots = base.get('spec', {}).get('slots', {})
            domain_slot_keys = set(spec.keys()) - {'kind', 'base'}

            errors = []
            for slot_name, slot_def in base_slots.items():
                mode = slot_def.get('mode')
                if mode == 'sealed' and slot_name in domain_slot_keys:
                    errors.append(f"sealed slot '{slot_name}' must not be overridden")
                elif mode == 'required' and slot_name not in domain_slot_keys:
                    errors.append(f"required slot '{slot_name}' is missing")

            if errors:
                for err in errors:
                    print(f"  \033[91m✗ {err}\033[0m")
                all_valid = False
            else:
                print(f"  \033[92m✓ OK\033[0m")
        except Exception as e:
            print(f"  \033[91m✗ ERROR: {e}\033[0m")
            all_valid = False

    if not all_valid:
        print("\nDomain compatibility check failed.")
        sys.exit(1)
    else:
        print(f"\nAll {len(domain_files)} DomainComposition files are compatible.")


def run_verify_release(artifact_path, strict=False, trust_root=None):
    """Verifies a PrimitiveRelease bundle: schema validation, build_hash, and meta_hash checks.

    strict=True: meta_hash mismatches against local source files are a hard failure.
    strict=False (default): meta_hash mismatches are reported as warnings only.
    """
    mode_label = " [STRICT]" if strict else ""
    print(f"--- Verifying release artifact: {artifact_path}{mode_label} ---")

    try:
        bundle = load_yaml(artifact_path)
    except Exception as e:
        print(f"\033[91m✗ ERROR: Cannot load artifact: {e}\033[0m")
        sys.exit(1)

    # Validate against release.schema.yaml if it exists
    release_schema_path = 'release.schema.yaml'
    if os.path.isfile(release_schema_path):
        try:
            from jsonschema import validate as jvalidate, ValidationError as JValidationError
            release_schema = load_yaml(release_schema_path)
            jvalidate(instance=bundle, schema=release_schema)
            print(f"  \033[92m✓ Schema valid (release.schema.yaml)\033[0m")
        except JValidationError as e:
            print(f"\033[91m✗ Schema validation failed: {e.message}\033[0m")
            sys.exit(1)
    else:
        print(f"  \033[93m⚠ release.schema.yaml not found — skipping schema validation\033[0m")

    if bundle.get('kind') != 'PrimitiveRelease':
        print(f"\033[91m✗ ERROR: Expected kind=PrimitiveRelease, got: {bundle.get('kind')}\033[0m")
        sys.exit(1)
    print(f"  kind:    PrimitiveRelease")
    print(f"  version: {bundle.get('version')}")
    print(f"  timestamp: {bundle.get('timestamp')}")

    specs = bundle.get('specs', [])
    print(f"  specs[]: {len(specs)} entries")

    validity = bundle.get('validity')
    created_by = bundle.get('createdBy')
    release_block = bundle.get('release', {})
    release_created_by = release_block.get('createdBy', {})

    # Verify developer commitment fields
    if not created_by or not created_by.get('certificate'):
        print(f"  \033[91m✗ createdBy.certificate missing — bundle lacks developer commitment\033[0m")
        sys.exit(1)
    print(f"  createdBy:  {created_by.get('name')} <{created_by.get('email')}>")

    # Verify release issuer fields
    if not release_created_by or not release_created_by.get('certificate'):
        print(f"  \033[91m✗ release.createdBy.certificate missing — release issuer not bound\033[0m")
        sys.exit(1)
    print(f"  releasedBy: {release_created_by.get('name')} <{release_created_by.get('email')}>")

    if validity:
        today = datetime.datetime.now(datetime.timezone.utc).date()
        valid_from = datetime.date.fromisoformat(validity.get('from', '1970-01-01'))
        valid_until = datetime.date.fromisoformat(validity.get('until', '1970-01-01'))
        if valid_from <= today <= valid_until:
            print(f"  \033[92m✓ Maintenance commitment valid: {valid_from} → {valid_until}\033[0m")
        else:
            print(f"  \033[93m⚠ Maintenance commitment expired: {valid_from} → {valid_until} (today: {today})\033[0m")
    else:
        print(f"  \033[93m⚠ No validity block found in bundle\033[0m")

    recorded_hash = release_block.get('build_hash', '')

    envelope_version = release_block.get('envelope', 1)
    if envelope_version not in (1, 2):
        print(f"  \033[91m✗ unknown release envelope version: {envelope_version}\033[0m")
        sys.exit(1)
    hash_payload = _release_hash_payload(bundle, envelope_version)
    recomputed_hash = get_sha256_b64(to_canonical_json(hash_payload))
    print(f"  release envelope: v{envelope_version}"
          f"{'  (legacy — signs four members only)' if envelope_version == 1 else ''}")

    if recomputed_hash == recorded_hash:
        print(f"\n  \033[92m✓ build_hash verified: {recomputed_hash[:24]}...\033[0m")
    else:
        print(f"\n  \033[91m✗ build_hash MISMATCH\033[0m")
        print(f"    recorded:   {recorded_hash}")
        print(f"    recomputed: {recomputed_hash}")
        sys.exit(1)

    # Optional: verify meta_hash against local source files if they exist
    mismatches = []
    for entry in specs:
        src = entry.get('source_path', '')
        recorded_meta = entry.get('meta_hash', '')
        if src and os.path.isfile(src):
            with open(src, 'rb') as fh:
                actual_meta = get_sha256_b64(fh.read())
            if actual_meta != recorded_meta:
                mismatches.append(f"{src}: recorded={recorded_meta[:12]}... actual={actual_meta[:12]}...")

    local_checked = sum(1 for e in specs if os.path.isfile(e.get('source_path', '')))

    if mismatches:
        label = "\033[91m✗\033[0m" if strict else "\033[93m⚠\033[0m"
        severity = "ERROR" if strict else "WARNING"
        print(f"\n  {label} meta_hash {severity}: source files differ from bundle ({len(mismatches)}/{local_checked}):")
        for m in mismatches:
            print(f"    {m}")
        if strict:
            print(f"  \033[91m✗ Strict mode: working tree must match the release bundle exactly.\033[0m")
            sys.exit(1)
    else:
        if local_checked:
            print(f"  \033[92m✓ meta_hash verified for {local_checked} local source files\033[0m")

    # Signature verification against release issuer certificate — mandatory
    print(f"\n--- Signature Verification ---")
    cert_pem = release_created_by.get('certificate', '')
    release_sign = release_block.get('sign', '')

    if not cert_pem:
        print(f"  \033[91m✗ release.createdBy.certificate missing — cannot verify signature\033[0m")
        sys.exit(1)
    if not release_sign:
        print(f"  \033[91m✗ release.sign missing — bundle is unsigned\033[0m")
        sys.exit(1)
    if not recorded_hash:
        print(f"  \033[91m✗ release.build_hash missing — cannot verify signature\033[0m")
        sys.exit(1)

    ok, reason = _verify_cert_signature(cert_pem, release_sign, recorded_hash)
    if ok:
        print(f"  \033[92m✓ Release signature verified (ECDSA, certificate public key)\033[0m")
    else:
        print(f"  \033[91m✗ Release signature FAILED: {reason}\033[0m")
        sys.exit(1)

    # Optional pledge signature verification if commitment.yaml is present
    if os.path.isfile('commitment.yaml'):
        try:
            commitment = load_yaml('commitment.yaml')
            pledge = commitment.get('pledge', {})
            pledge_hash = pledge.get('content_hash', '')
            pledge_sign = pledge.get('sign', '')
            pledge_cert = commitment.get('createdBy', {}).get('certificate', '')
            if pledge_cert and pledge_sign and pledge_hash:
                ok, reason = _verify_cert_signature(pledge_cert, pledge_sign, pledge_hash)
                if ok:
                    print(f"  \033[92m✓ Pledge signature verified (commitment.yaml)\033[0m")
                else:
                    print(f"  \033[91m✗ Pledge signature FAILED: {reason}\033[0m")
                    sys.exit(1)
        except Exception as e:
            print(f"  \033[93m⚠ Could not verify pledge signature: {e}\033[0m")
    else:
        print(f"  \033[93m⚠ commitment.yaml not found — pledge signature not verified\033[0m")

    # ── CIC counter-signature ───────────────────────────────────────────────
    #
    # The schema has described this block since v0.1.5 and the released bundle
    # carries a fully populated one — authority certificate, root certificate
    # and signature — while the verifier never looked at any of it. A bundle
    # whose countersign was replaced with garbage still reported success.
    print(f"\n--- CIC Counter-signature ---")
    countersign = bundle.get('cic_countersign')
    countersigned = False
    chain_ok = False
    root_fingerprint = None

    if not countersign:
        print(f"  \033[93m⚠ absent — this artifact carries no CIC counter-signature\033[0m")
    else:
        authority = countersign.get('authority', {}) or {}
        auth_name = authority.get('name', '(unnamed)')
        auth_cert = authority.get('certificate', '')
        auth_root = authority.get('root_certificate', '')
        payload_name = countersign.get('signed_payload', '')
        cs_sign = countersign.get('sign', '')

        if payload_name != 'build_hash':
            print(f"  \033[91m✗ signed_payload is '{payload_name}', not 'build_hash' — "
                  f"cannot tell what was signed\033[0m")
            sys.exit(1)
        if not auth_cert or not cs_sign:
            print(f"  \033[91m✗ authority certificate or signature missing\033[0m")
            sys.exit(1)

        ok, reason = _verify_cert_signature(auth_cert, cs_sign, recorded_hash)
        if not ok:
            print(f"  \033[91m✗ counter-signature FAILED: {reason}\033[0m")
            sys.exit(1)
        print(f"  \033[92m✓ counter-signature verified over build_hash ({auth_name})\033[0m")
        countersigned = True

        if not auth_root:
            print(f"  \033[93m⚠ no root_certificate — the authority certificate is unanchored\033[0m")
        else:
            ok, reason = _verify_cert_chain(auth_cert, auth_root)
            if not ok:
                print(f"  \033[91m✗ authority certificate does not chain to the root it "
                      f"carries: {reason}\033[0m")
                sys.exit(1)
            chain_ok = True
            root_fingerprint = _cert_fingerprint(auth_root)
            print(f"  \033[92m✓ authority certificate chains to the root in this bundle\033[0m")

    # ── Trust anchor ────────────────────────────────────────────────────────
    #
    # A root carried INSIDE the artifact is not a trust anchor: whoever can
    # rewrite the countersign can rewrite the root beside it. It only means
    # something when compared with a root obtained out of band.
    pinned = False
    if trust_root:
        if not os.path.isfile(trust_root):
            print(f"\n  \033[91m✗ trust root not found: {trust_root}\033[0m")
            sys.exit(1)
        with open(trust_root, 'r') as fh:
            pinned_pem = fh.read()
        pinned_fp = _cert_fingerprint(pinned_pem)
        if not pinned_fp:
            print(f"\n  \033[91m✗ trust root is not a readable PEM certificate\033[0m")
            sys.exit(1)
        if root_fingerprint is None:
            print(f"\n  \033[91m✗ --trust-root given, but this artifact carries no "
                  f"authority root to compare it against\033[0m")
            sys.exit(1)
        if pinned_fp != root_fingerprint:
            print(f"\n  \033[91m✗ TRUST ANCHOR MISMATCH — the artifact's root is not the "
                  f"pinned one\033[0m")
            print(f"      pinned:   {pinned_fp[:24]}...")
            print(f"      artifact: {root_fingerprint[:24]}...")
            sys.exit(1)
        pinned = True

    # ── What this run actually proved ───────────────────────────────────────
    #
    # The previous ending printed "CA chain verification not configured" and
    # then "Artifact integrity OK" on the next line. The second sentence was
    # stronger than the evidence: it is cryptographic self-consistency, not
    # provenance. Say exactly which claims hold.
    proven = [
        "the bundle matches release.schema.yaml",
        "build_hash equals a recomputation over {createdBy, releasedBy, specs, validity}",
        "release.sign verifies against the issuer certificate carried in the bundle",
    ]
    if countersigned:
        proven.append("cic_countersign verifies over build_hash with the authority certificate")
    if chain_ok:
        proven.append("the authority certificate was issued by the root carried in the bundle")
    if pinned:
        proven.append("that root is byte-identical to the out-of-band root you pinned")

    unproven = []
    if not countersigned:
        unproven.append("no CIC counter-signature is present")
    if countersigned and not chain_ok:
        unproven.append("the authority certificate is not anchored to any root")
    if not pinned:
        unproven.append("no external trust anchor was supplied (--trust-root), so every "
                        "certificate here is self-asserted")
    if envelope_version == 1:
        unproven.append("this is a v1 envelope: the signature covers four members only, "
                        "so kind, version, timestamp and provenance are unsigned and "
                        "can be rewritten without breaking build_hash")
    else:
        proven.append("the signature covers the whole bundle — kind, version, timestamp, "
                      "manifest and provenance included")
        if not (bundle.get('provenance') or {}).get('source_commit'):
            unproven.append("no source_commit recorded, so the artifact cannot be tied "
                            "back to a tree")

    print(f"\n--- What this proves ---")
    for claim in proven:
        print(f"  \033[92m✓\033[0m {claim}")
    for claim in unproven:
        print(f"  \033[93m·\033[0m NOT proven: {claim}")

    if unproven and strict:
        print(f"\n  \033[91m✗ --strict: an unproven claim remains\033[0m")
        sys.exit(1)

    if pinned:
        print(f"\n  \033[92m✓ Verified against the pinned CIC trust anchor\033[0m")
    else:
        print(f"\n  \033[92m✓ Internally consistent\033[0m — signed by the certificate this "
              f"artifact carries.")
        print(f"    That is not the same as trusted. Pass --trust-root <root.pem> to check "
              f"provenance.")


def main():
    """Main entrypoint for the script."""
    if len(sys.argv) < 2:
        print("Usage: python tools/compiler.py [validate|pledge|release|verify-release <artifact>]")
        sys.exit(1)

    command = sys.argv[1]

    if command in ('--help', '-h', 'help'):
        print("Usage: python tools/compiler.py <command>")
        print("")
        print("Commands:")
        print("  validate                             Validate all schemas offline (no Vault required).")
        print("  pledge                               Generate signed developer commitment → commitment.yaml.")
        print("  release                              Build signed PrimitiveRelease bundle (requires Vault + commitment.yaml).")
        print("  verify-release <artifact> [--strict] Verify a PrimitiveRelease bundle.")
        print("                                         Default: meta_hash mismatches are warnings.")
        print("                                         --strict: meta_hash mismatch is a hard failure.")
        print("  help                                 Show this help message.")
    elif command == 'validate':
        run_validation()
        run_primitive_validation()
        run_domain_compatibility_check()
    elif command == 'pledge':
        run_pledge()
    elif command == 'release':
        run_release()
    elif command == 'verify-release':
        if len(sys.argv) < 3:
            print("Usage: python tools/compiler.py verify-release <path/to/artifact.yaml> [--strict]")
            sys.exit(1)
        strict = '--strict' in sys.argv[3:]
        trust_root = None
        rest = sys.argv[3:]
        if '--trust-root' in rest:
            i = rest.index('--trust-root')
            if i + 1 >= len(rest):
                print("--trust-root needs a path to a PEM certificate")
                sys.exit(2)
            trust_root = rest[i + 1]
        run_verify_release(sys.argv[2], strict=strict, trust_root=trust_root)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
