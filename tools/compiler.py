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

    # 5. Build specs[] — per-schema hash over raw file bytes, inline content
    specs = []
    for schema_file in schema_files:
        with open(schema_file, 'rb') as fh:
            raw = fh.read()
        meta_hash = get_sha256_b64(raw)
        specs.append({
            'id': os.path.splitext(os.path.basename(schema_file))[0],
            'source_path': schema_file.replace(os.sep, '/'),
            'meta_hash': meta_hash,
            'spec': yaml.safe_load(raw),
        })
        print(f"  - {schema_file}: {meta_hash[:16]}...")

    # 6. Build hash: {createdBy (developer), release.createdBy (issuer), specs, validity}
    #    Both certificates are cryptographically bound before Vault signs.
    #    Future: this will become a Merkle tree root over CI artifact layers.
    hash_payload = {
        'createdBy': created_by,
        'releasedBy': release_created_by,
        'specs': specs,
        'validity': validity,
    }
    build_hash = get_sha256_b64(to_canonical_json(hash_payload))
    print(f"  - Build hash: {build_hash[:16]}...")

    # 7. Sign via Vault Transit (one call for the entire bundle)
    print(f"  - Signing with Vault key '{vault_key}'...")
    signature = _vault_sign(build_hash, vault_addr, vault_token, vault_key, verify_tls)
    print("  \033[92m✓ Vault signature obtained.\033[0m")

    # 8. Assemble and write the bundle artifact
    project_name = full_config.get('project', {}).get('name', 'XXprimitivesXX')
    bundle = {
        'kind': 'PrimitiveRelease',
        'version': release_version,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'validity': validity,
        'createdBy': created_by,
        'specs': specs,
        'release': {
            'createdBy': release_created_by,
            'build_hash': build_hash,
            'sign': signature,
        },
    }

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


def run_verify_release(artifact_path, strict=False):
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

    # build_hash covers {createdBy (developer), releasedBy (issuer), specs, validity}
    hash_payload = {
        'createdBy': created_by,
        'releasedBy': release_created_by,
        'specs': specs,
        'validity': validity,
    }
    recomputed_hash = get_sha256_b64(to_canonical_json(hash_payload))

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

    print(f"  \033[93m⚠ CA chain verification not configured (no trust root bundle)\033[0m")
    print(f"\n  \033[92m✓ Artifact integrity OK\033[0m")


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
        run_verify_release(sys.argv[2], strict=strict)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
