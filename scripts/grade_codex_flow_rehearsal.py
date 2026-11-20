"""Grade the Codex rehearsal artifact with the frozen CSV and three checks."""
import argparse
import csv
import json
from pathlib import Path


def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError('Duplicate JSON key')
    return result


def grade(source, artifact):
    if not artifact.is_file():
        return {'status': 'missing_artifact', 'score': None, 'max_score': 3}
    with source.open(encoding='utf-8', newline='') as stream:
        eligible = [row for row in csv.DictReader(stream) if row['status'] == 'settled']
    ids = [row['id'] for row in eligible]
    net_cents = sum(int(row['gross_cents']) - int(row['refund_cents']) for row in eligible)
    try:
        result = json.loads(artifact.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object)
    except ValueError:
        result = None
    if not isinstance(result, dict):
        result = {}
    observed_ids = result.get('settled_ids')
    observed_net = result.get('net_cents')
    typed_ids = isinstance(observed_ids, list) and all(isinstance(item, str) for item in observed_ids)
    typed_net = type(observed_net) is int
    checks = {'schema': set(result) == {'settled_ids', 'net_cents'} and typed_ids and typed_net,
              'ordered_ids': typed_ids and observed_ids == ids,
              'net_integer': typed_net and observed_net == net_cents}
    return {'status': 'scored', 'score': sum(checks.values()), 'max_score': 3, 'checks': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--check', action='store_true', help='Compare with score.json next to the artifact.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    fixture = root / 'supplements/codex-flow-rehearsal-v1/transactions.csv'
    scored = grade(fixture, args.artifact)
    if args.check and scored != json.loads(args.artifact.with_name('score.json').read_bytes()):
        raise ValueError('Archived rehearsal score differs from recomputation.')
    print(json.dumps(scored, indent=2))


if __name__ == '__main__':
    main()
