"""Package source and recorded evidence; never train or modify frozen artifacts."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {'.git', 'node_modules', 'bin', 'obj', 'dist', '__pycache__',
                '.venv', '.vs', '.idea', '.vscode', 'TestResults', 'playwright-report',
                'objtemp', 'artifacts', 'packages'}
SOURCE_ROOTS = ('backend', 'frontend', 'research', 'docs', 'sketch_dec15a', 'tools')
EVIDENCE = ('fixes-backend-build.log', 'fixes-tests.log', 'fixes-frontend-tests.log',
            'fixes-frontend-build.log', 'fixes-lint.log', 'npm-audit-final.json',
            'research-tests-final.log', 'toc-checks.json', 'ui-verification-final.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def walk(base):
    for directory, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for name in sorted(names):
            if name == 'appsettings.Development.json':
                continue
            if name == 'device_secrets.h' or name.startswith('.env'):
                if name not in ('.env.example', '.env.sample'):
                    continue
            if name.endswith(('.pyc', '.pyo', '.nbi', '.nbc', '.tsbuildinfo', '.user', '.suo')):
                continue
            yield Path(directory) / name


def select_files():
    files = set()
    for name in SOURCE_ROOTS:
        files.update(walk(ROOT / name))
    for name in ('README.md', 'agents.md', '.gitignore'):
        files.add(ROOT / name)
    # Preserve earlier negative results and exact model dependencies. Exclude the
    # multi-GB raw download and disposable intermediate database/parsed copy.
    for base in sorted((ROOT / '.codex-work').glob('parking-*')):
        for p in walk(base):
            rel = p.relative_to(base)
            if base.name == 'parking-research-phase2-20261018':
                if p.name in ('preparation.duckdb', 'parsed.parquet'):
                    continue
                if rel.parts[0] == 'source' and p.suffix not in ('.json', '.html', '.md', '.txt'):
                    continue
            files.add(p)
    audit = ROOT / '.codex-work/readiness-audit-20261101'
    for name in EVIDENCE:
        files.add(audit / name)
    files.add(ROOT / '.codex-work/arduino-validation/compile.log')
    return sorted(files)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    files = select_files()
    missing = [str(p.relative_to(ROOT)) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    frozen = json.loads((ROOT / 'docs/research/adaptive-sampling/phase4-delivery-artifacts.json').read_text(encoding='utf-8'))['files']
    selected = {p.relative_to(ROOT).as_posix() for p in files}
    if set(frozen) - selected:
        raise ValueError('Some frozen artifacts were not selected')
    # Compare private literals internally. Never print their values or hashes.
    private_header = ROOT / 'sketch_dec15a/device_secrets.h'
    private_literals = []
    if private_header.exists():
        for line in private_header.read_text(encoding='utf-8').splitlines():
            if re.search(r'WIFI_PASS|DEVICE_KEY', line, re.I):
                match = re.search(r'"([^"\n]+)"', line)
                if match and len(match[1]) >= 8:
                    private_literals.append(match[1].encode())
    manifest = {}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in files:
            name = p.relative_to(ROOT).as_posix()
            data = p.read_bytes()
            if any(secret in data for secret in private_literals):
                raise ValueError('Private credential found in selected file: ' + name)
            if name in frozen and sha(data) != frozen[name]:
                raise ValueError('Frozen file changed: ' + name)
            if name.endswith('.json') and 'appsettings' in p.name:
                # Block real connection-string credentials, but retain local
                # trusted connections and empty example fields.
                for assignment in re.findall(rb'(?:SharedAccessKey|AccountKey|Password)=([^;"\s]+)', data, re.I):
                    if assignment and not re.search(rb'YOUR|REPLACE|EXAMPLE|PLACEHOLDER|<', assignment, re.I):
                        raise ValueError('Credential-bearing configuration: ' + name)
            archive.writestr(name, data)
            manifest[name] = {'sha256': sha(data), 'bytes': len(data)}
        meta = {'created_on': '2026-11-01', 'files': manifest,
                'frozen_research_files': len(frozen), 'raw_archive_included': False,
                'private_device_config_included': False}
        archive.writestr('DELIVERY-MANIFEST.json', json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    # Independently read every member back and verify the uncompressed content.
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive CRC failure')
        for name, expected in manifest.items():
            data = archive.read(name)
            if sha(data) != expected['sha256'] or len(data) != expected['bytes']:
                raise ValueError('Archive readback failure: ' + name)
    result = {'archive': str(args.output.resolve()), 'files': len(manifest),
              'frozen_files': len(frozen), 'bytes': args.output.stat().st_size,
              'sha256': sha(args.output.read_bytes()), 'archive_readback_passed': True}
    args.output.with_suffix('.verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
