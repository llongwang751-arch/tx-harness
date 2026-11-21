"""Check the DSH-locked settlement exercise against its registered scoring assets."""
import argparse
import csv
import json
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_csv(path, header):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames
        rows = list(reader)
    if fields != header or any(None in row or None in row.values() for row in rows):
        raise ValueError('Unexpected CSV schema')
    return rows


def grade(outputs, assets):
    reference = read_json(assets / 'reference.json')
    oracle = read_json(assets / 'oracle.json')
    manifest = read_json(assets / 'rubric.json')
    if manifest['case'] != 'dsh-locked-settlement-v1':
        raise ValueError('Rubric belongs to a different evaluation.')
    rubric = manifest['weights']
    checks = dict.fromkeys(rubric, False)
    ledger, summary, rejects = None, None, None
    try:
        ledger = read_csv(outputs / 'ledger.csv', reference['ledger_header'])
        checks['eligible_order_ids'] = [(row['order_id'], row['vendor_id']) for row in ledger] == [tuple(pair) for pair in oracle['eligible']]
        amounts = [{key: int(row[key]) for key in reference['amount_fields']} for row in ledger]
        checks['ledger_amounts'] = amounts == reference['amounts']
    except (OSError, ValueError, csv.Error):
        pass
    try:
        rejects = read_csv(outputs / 'rejects.csv', ['order_id', 'reason'])
        checks['rejections_and_priority'] = rejects == oracle['rejections']
    except (OSError, ValueError, csv.Error):
        pass
    try:
        summary = read_json(outputs / 'summary.json')
        if not isinstance(summary, dict) or set(summary) != set(reference['summary']) or any(type(v) is not int for v in summary.values()):
            raise ValueError('Unexpected summary schema')
        checks['summary_exact'] = summary == reference['summary']
        if ledger is not None and rejects is not None:
            checks['internal_reconciliation'] = summary == {
                'eligible_count': len(ledger), 'rejected_count': len(rejects),
                'total_fee_cents': sum(int(row['fee_cents']) for row in ledger),
                'total_payable_cents': sum(int(row['payable_cents']) for row in ledger),
            }
    except (OSError, ValueError, TypeError):
        pass
    return {'score': sum(rubric[key] for key, passed in checks.items() if passed),
            'max_score': sum(rubric.values()), 'checks': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outputs', type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='Compare to ../score.json next to the outputs directory.')
    args = parser.parse_args()
    result = grade(args.outputs, Path(__file__).resolve().parent)
    if args.check and result != read_json(args.outputs.parent / 'score.json'):
        raise ValueError('Archived result differs from recomputation.')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
