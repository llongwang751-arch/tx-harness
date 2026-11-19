"""Recompute the five-product engineering results from reviewed, public evidence."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness_eval.core import read_json, sha256

STIMULUS = ROOT / 'supplements/five-surface-v1'
PUBLIC = ROOT / 'public/five-surface-20261119'
REGISTRATION = '7876f914bdbee57c6b19a1d1bfa53f1190bdd77d'


def parse_receipt(text):
    def unique_fields(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError('Duplicate answer fields')
        return value

    try:
        data = json.loads(text, object_pairs_hook=unique_fields)
    except ValueError:
        return None
    if (not isinstance(data, dict) or set(data) != {'records', 'total_cents'}
            or type(data['total_cents']) is not int
            or not isinstance(data['records'], list)
            or any(not isinstance(row, str) for row in data['records'])):
        return None
    return data


def parse_answer(text):
    fenced = re.findall(r'```(?:json)?\s*(\{[^{}]*\})\s*```', text, re.I)
    candidates = fenced or re.findall(r'\{[^{}]*\}', text)
    return parse_receipt(candidates[0]) if len(candidates) == 1 else None


def audit():
    for name in ('input.csv', 'prompt.txt', 'protocol.json'):
        frozen = subprocess.check_output(
            ['git', 'show', f'{REGISTRATION}:supplements/five-surface-v1/{name}'], cwd=ROOT)
        if (STIMULUS / name).read_bytes() != frozen:
            raise ValueError(f'{name}: differs from the preregistered version')
    with (STIMULUS / 'input.csv').open(encoding='utf-8', newline='') as stream:
        rows = [row for row in csv.DictReader(stream) if row['state'] == 'settled']
    expected = {'records': [row['record'] for row in rows], 'total_cents': sum(int(row['amount_cents']) for row in rows)}
    digest = sha256(STIMULUS / 'input.csv')
    results = {}
    intervals = []
    for product, run_id in read_json(STIMULUS / 'protocol.json')['run_ids'].items():
        folder = PUBLIC / run_id
        record = read_json(folder / 'observation.json')
        if record['run_id'] != run_id or record['product'] != product:
            raise ValueError(f'{product}: run identifier mismatch')
        if record.get('accepted') and record.get('input_sha256') != digest:
            raise ValueError(f'{product}: submitted input receipt does not match the frozen CSV')
        if record.get('accepted'):
            submitted = datetime.fromisoformat(record['submitted_at'])
            ended = datetime.fromisoformat(record['ended_at'])
            if not 0 <= (ended - submitted).total_seconds() <= 180:
                raise ValueError(f'{product}: invalid interval or preregistered deadline exceeded')
            intervals.append((submitted, ended, product))
        if record.get('completed') and not record.get('accepted'):
            raise ValueError(f'{product}: completion requires task acceptance')
        excerpt = folder / 'native-events.excerpts.json'
        if 'public_excerpt_sha256' in record and sha256(excerpt) != record['public_excerpt_sha256']:
            raise ValueError(f'{product}: native excerpt digest differs')
        artifact = folder / 'receipt.json'
        if artifact.is_file() != record.get('artifact_observed', False):
            raise ValueError(f'{product}: native file has no matching collection record')
        reply = record.get('final_reply')
        artifact_result = 'not_obtained'
        if artifact.is_file():
            if sha256(artifact) != record['artifact_sha256'] or artifact.stat().st_size != record['artifact_bytes']:
                raise ValueError(f'{product}: preserved artifact bytes differ')
            try:
                parsed_artifact = parse_receipt(artifact.read_text(encoding='utf-8-sig'))
            except UnicodeError:
                parsed_artifact = None
            artifact_result = 'pass' if parsed_artifact == expected else 'fail'
        results[product] = {'run_id': run_id, 'accepted': record.get('accepted', False),
                            'completed': record.get('completed', False),
                            'reply': 'not_obtained' if reply is None else 'pass' if parse_answer(reply) == expected else 'fail',
                            'artifact': artifact_result,
                            'evidence_sha256': sha256(folder / 'observation.json')}

    intervals.sort()
    for (_, previous_end, previous), (next_start, _, current) in zip(intervals, intervals[1:]):
        if next_start < previous_end:
            raise ValueError(f'{previous} and {current}: product intervals overlap')

    counts = dict.fromkeys(('accepted', 'valid_pass', 'valid_fail', 'unknown'), 0)
    for result in results.values():
        counts['accepted'] += int(result['accepted'])
        checks = {result['reply'], result['artifact']}
        if not result['completed'] or 'not_obtained' in checks:
            counts['unknown'] += 1
        elif 'fail' in checks:
            counts['valid_fail'] += 1
        else:
            counts['valid_pass'] += 1
    return {'schema': 'tx-harness/five-surface-transfer-result/v1', 'registration_commit': REGISTRATION,
            'input_sha256': digest, 'prompt_sha256': sha256(STIMULUS / 'prompt.txt'),
            'counts': counts, 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = audit()
    target = PUBLIC / 'results.json'
    if args.check:
        if data != read_json(target):
            raise ValueError('Published transfer results are stale')
    else:
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                          encoding='utf-8', newline='\n')
    print(json.dumps(data, ensure_ascii=False))


if __name__ == '__main__':
    main()
