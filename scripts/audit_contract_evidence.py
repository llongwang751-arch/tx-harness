"""Resolve public review locators without changing sealed evidence or verdicts.

File/event resolution establishes inspectability, not the truth of a judgment.
Nested source descriptors identify private provenance, not public-file promises.
Free-text references remain manual notes and never become verified locators.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath

from contract_v2 import ROOT, BASE, inventory, read, save, sha

PUBLIC = ROOT / 'public/supplements/contracts-v2'
SEALED_COMMIT = '3d1c7b931b08f62cf4333797b98587c91d17b0dc'


def contained_file(base, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Invalid relative evidence path')
    rel = PurePosixPath(name)
    if rel.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Evidence path escapes its package')
    path = Path(base) / name
    if not path.resolve().is_relative_to(Path(base).resolve()) or path.is_symlink():
        raise ValueError('Evidence path escapes its package')
    return path


def attachment_plan(private, review, published_files):
    """Explicitly reviewed attachments only; reject omissions before export writes."""
    from run_native_office_pilot import safe_public_text
    declared = review.get('public_attachment_files', [])
    if not isinstance(declared, list) or any(not isinstance(x, str) for x in declared) or len(set(declared)) != len(declared):
        raise ValueError('Invalid reviewed attachment allowlist')
    copies = {}
    for name in declared:
        source = contained_file(private, name)
        if name in published_files or not source.is_file():
            raise ValueError('Attachment collides with export or is missing: ' + name)
        safe_public_text(source.read_text(encoding='utf-8'))
        copies[name] = source
    for observation in review['observations'].values():
        if not isinstance(observation, dict):
            continue
        for evidence in observation.get('evidence', []):
            if not isinstance(evidence, dict) or 'file' not in evidence:
                continue
            name = evidence['file']
            contained_file(private, name)
            if name not in published_files and name not in copies:
                raise ValueError('Referenced attachment needs explicit privacy review: ' + name)
            if name in copies and 'sha256' in evidence and sha(copies[name]) != evidence['sha256']:
                raise ValueError('Reviewed attachment hash mismatch: ' + name)
    return copies


def load_addenda(public):
    index = read(public / 'evidence-addenda/index.json')
    entries = {}
    for entry in index['files']:
        key = (entry['slot_id'], entry['referenced_file'])
        if key in entries:
            raise ValueError('Duplicate addendum mapping')
        package = contained_file(public, entry['slot_id'])
        contained_file(package, entry['referenced_file'])
        attachment = contained_file(public / 'evidence-addenda', entry['public_file'])
        if sha(attachment) != entry['sha256']:
            raise ValueError('Addendum bytes changed: ' + entry['public_file'])
        metadata = package / 'metadata.json'
        if sha(metadata) != entry['source_metadata_sha256']:
            raise ValueError('Sealed metadata changed')
        if read(metadata)['raw_records_sha256'].get(entry['referenced_file']) != entry['sha256']:
            raise ValueError('Addendum not anchored in sealed source hashes')
        entries[key] = {**entry, 'path': attachment}
    return entries


def audit_package(package, addenda):
    actual = inventory(package)
    actual.pop('manifest.json')
    if actual != read(package / 'manifest.json'):
        raise ValueError('Sealed package manifest mismatch: ' + package.name)
    events = {}
    for line in (package / 'visible-events.jsonl').read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        event_id = event['event_id']
        if event_id in events:
            raise ValueError('Ambiguous event locator: ' + event_id)
        events[event_id] = event
    results = []
    for metric, observation in read(package / 'review.json')['observations'].items():
        if not isinstance(observation, dict):
            continue
        for number, evidence in enumerate(observation.get('evidence', [])):
            row = {'slot_id': package.name, 'metric': metric, 'evidence_index': number,
                   'resolutions': []}
            if isinstance(evidence, dict) and 'file' in evidence:
                name = evidence['file']
                target = contained_file(package, name)
                kind = 'package_file'
                if not target.is_file():
                    entry = addenda.get((package.name, name))
                    if entry is None:
                        raise ValueError(f'Missing public evidence: {package.name}/{name}')
                    target = entry['path']
                    kind = 'anchored_addendum'
                digest = sha(target)
                if 'sha256' in evidence and evidence['sha256'] != digest:
                    raise ValueError(f'Evidence hash mismatch: {package.name}/{name}')
                row['resolutions'].append({'kind': kind, 'file': name, 'sha256': digest,
                    'public_file': (target.relative_to(package).as_posix() if kind == 'package_file'
                                    else '../evidence-addenda/' + entry['public_file']),
                    'declared_hash_present': 'sha256' in evidence})
            if isinstance(evidence, dict) and 'event_id' in evidence:
                if evidence['event_id'] not in events:
                    raise ValueError('Missing public event: ' + str(evidence['event_id']))
                row['resolutions'].append({'kind': 'public_event', 'event_id': evidence['event_id']})
            if not row['resolutions']:
                row.update(status='manual_note', note=evidence)
            else:
                row['status'] = 'resolved_locator'
            results.append(row)
    return results


def build(public=PUBLIC):
    # Check the old bytes against their actual published commit, not just a new
    # editable manifest. These 21 slots are a closed historical experiment batch.
    specs = read(BASE / 'protocol.json')['slots']
    original_paths = [(public / s['slot_id']).relative_to(ROOT).as_posix() for s in specs]
    changed = subprocess.check_output(['git', 'diff', '--name-only', SEALED_COMMIT,
                                      '--', *original_paths], cwd=ROOT, text=True)
    if changed.strip():
        raise ValueError('Historical sealed evidence changed: ' + changed.strip())
    if read(public / 'evidence-addenda/index.json')['sealed_source_commit'] != SEALED_COMMIT:
        raise ValueError('Unexpected source evidence commit')
    addenda = load_addenda(public)
    rows = []
    used = set()
    for spec in specs:
        package = public / spec['slot_id']
        if not (package / 'manifest.json').is_file():
            continue
        items = audit_package(package, addenda)
        rows.extend(items)
        used.update((r['slot_id'], x['file']) for r in items for x in r['resolutions']
                    if x['kind'] == 'anchored_addendum')
    if used != set(addenda):
        raise ValueError('Unused or unverified addendum entry')
    counts = Counter(x['kind'] for r in rows for x in r['resolutions'])
    return {'schema': 'contract-v2-public-locator-audit', 'audit_date': '2026-10-20',
        'summary': {'review_evidence_entries': len(rows), **dict(sorted(counts.items())),
                    'addendum_files': len(addenda),
                    'manual_notes': sum(r['status'] == 'manual_note' for r in rows),
                    'unresolved_structured_locators': 0},
        'limits': 'Locator resolution and hash equality do not validate semantic judgments, private provenance, or causal attribution. Free-text notes require manual review.',
        'rows': rows}


def markdown(data):
    s = data['summary']
    index = read(PUBLIC / 'evidence-addenda/index.json')
    lines = ['# 补测公开证据定位审计', '',
        '2026-10-20仓库复核发现：原导出器遗漏了6份已脱敏核查附件。四项主观察有12处引用受影响；连同额外交付/声明观察，共17处。原包不覆盖，补充公开的字节与原metadata及review内的SHA完全一致。此次补充不是重做实验，也未改判或改分。', '',
        f"当前核对{s['review_evidence_entries']}条evidence：包内文件定位{s.get('package_file', 0)}处、补充附件定位{s.get('anchored_addendum', 0)}处、公开event_id定位{s.get('public_event', 0)}处；结构化定位缺失0处。另有{s['manual_notes']}条说明性/非结构化引用仍需人工阅读，不将其算成机器已验证的事件。", '',
        '| 原实验位 | 原引用文件 / 补充公开位置 | SHA依据 |', '|---|---|---|']
    for entry in index['files']:
        lines.append(f"| {entry['slot_id']} | [{entry['referenced_file']}](evidence-addenda/{entry['public_file']}) | 原包metadata.raw_records_sha256及review |")
    lines += ['',
        '复核：`python -X utf8 scripts/audit_contract_evidence.py --check`。逐条结果见[evidence-locators.json](evidence-locators.json)，映射和原包metadata摘要见[附件索引](evidence-addenda/index.json)。CI另核验原包manifest；此检查只验证定位与字节一致性，不能自动认可观察项的语义、现场真实性或因果结论。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = build()
    md = markdown(data)
    if args.check:
        if read(PUBLIC / 'evidence-locators.json') != data:
            raise ValueError('Evidence locator JSON drift')
        if (PUBLIC / 'evidence-locators.md').read_text(encoding='utf-8') != md:
            raise ValueError('Evidence locator Markdown drift')
    else:
        save(PUBLIC / 'evidence-locators.json', data)
        (PUBLIC / 'evidence-locators.md').write_text(md, encoding='utf-8', newline='\n')
    print(json.dumps(data['summary']))


if __name__ == '__main__':
    main()
