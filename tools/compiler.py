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
        stdout=subprocess.PIPE
    )
    # Hash the tar stream
    digest_proc = subprocess.Popen(
        ['openssl', 'dgst', '-sha256', '-binary'],
        stdin=archive_proc.stdout,
        stdout=subprocess.PIPE
    )
    # Base64 encode the hash
    b64_proc = subprocess.Popen(
        ['openssl', 'base64', '-A'],
        stdin=digest_proc.stdout,
        stdout=subprocess.PIPE,
        text=True
    )
    archive_proc.stdout.close()  # Allow archive_proc to receive a SIGPIPE

    repo_hash_b64 = b64_proc.communicate()[0].strip()

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

    # Sanitize the component name by removing any trailing '/main' or '|main'
    # to ensure it represents the core component prefix.
    raw_component_name = project_config.get('main_branch', 'main')
    print(f"'{raw_component_name}'")
    component_name = re.sub(r'main$', '', raw_component_name)
    print(f"'{component_name}'")

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


def run_release():
    """Runs the full release process: validation, checksum, signing."""
    print("--- Running Schema Release ---")
    # First, run all prerequisite checks
    release_version, component_name = validate_release_prerequisites()

    vault_addr = os.getenv('VAULT_ADDR')
    vault_token = os.getenv('VAULT_TOKEN')
    vault_cacert = os.getenv('VAULT_CACERT')  # For production TLS verification

    if not vault_addr or not vault_token:
        print("[FATAL] VAULT_ADDR and VAULT_TOKEN must be set for release.")
        sys.exit(1)

    # Set TLS verification for Vault connection
    if vault_cacert:
        verify_tls = vault_cacert
        print(f"[INFO] Using CA cert for Vault TLS verification: {vault_cacert}")
    else:
        verify_tls = False
        print("\033[93m[WARNING] Vault TLS verification is disabled. Do not use in production.\033[0m")

    # 1. Prepare project.yaml with version and timestamp
    full_project_config = load_project_config(full_config=True)
    if 'release' in full_project_config:
        del full_project_config['release']

    release_block = {
        "version": release_version,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    full_project_config['release'] = release_block
    write_yaml('project.yaml', full_project_config)
    print("  - Updated project.yaml with version and timestamp.")

    # 2. Stage all changes and get the repository tree hash (source_hash)
    print("  - Staging all changes to calculate repository state...")
    run_git_command(['git', 'add', '.'])
    tree_id = run_git_command(['git', 'write-tree'])
    print(f"  - Staged content tree ID: {tree_id[:12]}...")
    source_hash = get_reproducible_repo_hash(tree_id)
    print(f"  - Calculated source hash: {source_hash[:12]}...")

    # 3. build_hash = source_hash egyelőre — tényleges build env nincs még
    build_hash = source_hash
    print(f"  - Build hash (= source hash until real build env): {build_hash[:12]}...")

    # 4. Write release block to project.yaml (release.sh adds sign + cert on top)
    release_block['repository_tree_hash'] = source_hash
    release_block['build_hash'] = build_hash
    full_project_config['release'] = release_block
    write_yaml('project.yaml', full_project_config)
    print("  - \033[92m✓ project.yaml finalized with source_hash + build_hash.\033[0m")
    print(f"  - \033[93mACTION REQUIRED: git tag {component_name}@v{release_version}\033[0m")


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


def main():
    """Main entrypoint for the script."""
    if len(sys.argv) < 2:
        print("Usage: python tools/compiler.py [validate|release]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'validate':
        run_validation()
        run_primitive_validation()
        run_domain_compatibility_check()
    elif command == 'release':
        run_release()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
