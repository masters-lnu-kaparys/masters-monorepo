"""Download and checksum the official Melbourne archive and its metadata."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.error
import urllib.request
import zipfile

ARCHIVE = 'https://opendatasoft-s3.s3.amazonaws.com/downloads/archive/7pgd-bdf2.zip'
METADATA = {
    'official_page': 'https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/',
    'official_api': 'https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/on-street-car-parking-sensor-data-2019',
    'datavic_api': 'https://discover.data.vic.gov.au/api/3/action/package_show?id=on-street-car-parking-sensor-data-2019',
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def request(url: str, headers=None):
    return urllib.request.Request(url, headers={'User-Agent': 'University parking sampling research; source preservation', **(headers or {})})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--download-workers', type=int, default=8)
    args = parser.parse_args()
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    source = work / 'source'
    source.mkdir(exist_ok=True)
    report = {'captured_at_utc': datetime.now(timezone.utc).isoformat(), 'archive_url': ARCHIVE, 'metadata': {}}
    for key, url in METADATA.items():
        try:
            with urllib.request.urlopen(request(url), timeout=25) as response:
                body = response.read()
                suffix = '.json' if 'json' in response.headers.get('Content-Type', '') else '.html'
                dest = source / (key + suffix)
                dest.write_bytes(body)
                report['metadata'][key] = {'url': url, 'status': response.status, 'file': dest.name, 'sha256': sha256(dest)}
                if suffix == '.json':
                    payload = json.loads(body)
                    if key == 'official_api':
                        report['metadata'][key]['default_metas'] = payload.get('metas', {}).get('default', {})
                    if key == 'datavic_api':
                        result = payload.get('result', {})
                        report['metadata'][key]['license'] = {k: result.get(k) for k in ('license_id', 'license_title', 'license_url')}
                print(f'metadata {key}: saved {len(body)} bytes', flush=True)
        except Exception as exc:
            report['metadata'][key] = {'url': url, 'error': str(exc)}
            print(f'metadata {key}: {exc}', flush=True)
    dest = source / 'melbourne-2019.zip'
    partial = source / 'melbourne-2019.zip.partial'
    if dest.exists():
        print(f'reusing local archive, bytes={dest.stat().st_size}', flush=True)
    else:
        start = time.monotonic()
        head = urllib.request.Request(ARCHIVE, method='HEAD')
        with urllib.request.urlopen(head, timeout=30) as response:
            total = int(response.headers['Content-Length'])
            report['archive_response_headers'] = dict(response.headers)
        chunk_size = 16 * 1024 * 1024
        chunks = source / 'download-parts'
        chunks.mkdir(exist_ok=True)
        if partial.exists():
            # Reuse complete chunks from the earlier sequential attempt.
            with partial.open('rb') as previous:
                for index in range(partial.stat().st_size // chunk_size):
                    chunk = previous.read(chunk_size)
                    chunk_path = chunks / f'{index:04d}.part'
                    if not chunk_path.exists():
                        chunk_path.write_bytes(chunk)
        def fetch_chunk(index):
            lo = index * chunk_size
            hi = min(total, lo + chunk_size) - 1
            path = chunks / f'{index:04d}.part'
            if path.exists() and path.stat().st_size == hi-lo+1:
                return path
            for attempt in range(1,5):
                try:
                    with urllib.request.urlopen(request(ARCHIVE, {'Range':f'bytes={lo}-{hi}'}), timeout=60) as response:
                        if response.status != 206 or response.headers.get('Content-Range') != f'bytes {lo}-{hi}/{total}':
                            raise IOError('Server did not honor the requested bounded byte range')
                        stage = path.with_suffix('.partial')
                        with stage.open('wb') as stream:
                            shutil.copyfileobj(response,stream,length=256*1024)
                        if stage.stat().st_size != hi-lo+1:
                            raise IOError('Incomplete bounded download')
                        stage.replace(path)
                    return path
                except (OSError,urllib.error.URLError) as exc:
                    if attempt==4:
                        raise
                    print(f'chunk {index} retry {attempt}: {exc}',flush=True)
        count = (total + chunk_size - 1) // chunk_size
        with ThreadPoolExecutor(max_workers=args.download_workers) as executor:
            futures = [executor.submit(fetch_chunk,index) for index in range(count)]
            for done,future in enumerate(as_completed(futures),1):
                future.result()
                print(f'download chunks {done}/{count}, elapsed={time.monotonic()-start:.1f}s',flush=True)
        assembly = source/'melbourne-2019.zip.assembling'
        with assembly.open('wb') as writer:
            for index in range(count):
                with (chunks/f'{index:04d}.part').open('rb') as reader:
                    shutil.copyfileobj(reader,writer,length=4*1024*1024)
        if assembly.stat().st_size != total:
            raise IOError('Assembled archive size mismatch')
        assembly.replace(dest)
        report['download_elapsed_seconds'] = round(time.monotonic() - start, 2)
    report['archive_bytes'] = dest.stat().st_size
    report['archive_sha256'] = sha256(dest)
    with zipfile.ZipFile(dest) as archive:
        entries = archive.infolist()
        report['archive_entries'] = [{'name': v.filename, 'bytes': v.file_size, 'compressed_bytes': v.compress_size, 'crc32': f'{v.CRC:08x}'} for v in entries]
        csv_entries = [v for v in entries if v.filename.lower().endswith('.csv') and not v.is_dir()
                       and not v.filename.startswith('__MACOSX/') and not Path(v.filename).name.startswith('._')]
        if len(csv_entries) != 1:
            raise ValueError('Expected exactly one CSV entry')
        entry = csv_entries[0]
        csv_path = source / 'melbourne-2019.csv'
        if not csv_path.exists() or csv_path.stat().st_size != entry.file_size:
            print(f'extract and validate CRC: {entry.file_size} uncompressed bytes', flush=True)
            with archive.open(entry) as reader, csv_path.open('wb') as writer:
                shutil.copyfileobj(reader, writer, length=8 * 1024 * 1024)
            # Reading the entry to EOF verifies its ZIP CRC in Python's ZipExtFile.
        else:
            # Existing extraction must also be independently CRC-checked before reuse.
            with archive.open(entry) as reader:
                for _ in iter(lambda: reader.read(8 * 1024 * 1024), b''):
                    pass
        report['csv_path'] = csv_path.name
        report['csv_bytes'] = csv_path.stat().st_size
        report['csv_sha256'] = sha256(csv_path)
        report['csv_crc_verified'] = True
        for other in entries:
            if other != entry and not other.is_dir():
                with archive.open(other) as reader:
                    for _ in iter(lambda: reader.read(1024*1024),b''):
                        pass
        report['all_archive_entry_crcs_verified'] = True
    (source / 'source-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'metadata'}, ensure_ascii=False, indent=2), flush=True)

if __name__ == '__main__':
    main()
