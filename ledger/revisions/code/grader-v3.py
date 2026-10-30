"""Add validity gates to the frozen artifact checks without rewriting scores."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from harness_eval import core

RULE_FILE = core.ROOT / 'supplements/grader-v3/rules.json'


def decoded_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from decoded_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from decoded_strings(item)


def adjudicate(case_id, outputs, *, disabled_rules=()):
    rules = core.read_json(RULE_FILE)
    disabled = set(disabled_rules)
    if not disabled <= set(rules['rules']):
        raise ValueError('Unknown ablation rule')
    if case_id not in core.read_json(core.ROOT / 'config/protocol.json')['case_ids']:
        raise ValueError('Unknown case')
    outputs = Path(outputs)
    case_dir = core.ROOT / 'cases' / case_id
    case, _ = core.load_case(case_dir)
    legacy = core.evaluate(case_dir, outputs)
    guards = []

    def check(rule, relative, inspect):
        if rule in disabled:
            return
        record = {'rule_id': rule, 'path': relative, 'passed': False,
                  'artifact_sha256': None, 'reason': ''}
        try:
            path = core.inside(outputs, relative)
            record['artifact_sha256'] = core.sha256(path)
            record['passed'], record['reason'] = inspect(path)
        except OSError as error:
            record['reason'] = f'{type(error).__name__}: delivery file unavailable'
        except (ValueError, TypeError, KeyError, csv.Error) as error:
            record['reason'] = f'{type(error).__name__}: {error}'
        guards.append(record)

    def strict_csv(path):
        with path.open(encoding='utf-8-sig', newline='') as handle:
            for _ in csv.reader(handle, strict=True):
                pass
        return True, 'Strict parser accepted; column/key/value checks remain legacy checks'

    for target in sorted({c['config']['path'] for c in case['checks'] if c['kind'] == 'csv_rows'}):
        check('CSV_STRICT', target, strict_csv)
    for target, keys in rules['exact_top_level_keys'].get(case_id, {}).items():
        def exact_keys(path, expected=keys):
            data = core.read_json(path)
            ok = isinstance(data, dict) and set(data) == set(expected)
            return ok, 'Exact top-level key set matched' if ok else 'Unexpected or missing top-level key'
        check('T03_CHANGELOG_KEYS', target, exact_keys)
    for item in case['checks']:
        cfg = item['config']
        if item['kind'] != 'text_excludes' or not cfg['path'].endswith('.json'):
            continue
        def no_decoded_marker(path, forbidden=cfg['values']):
            hits = sorted({needle for text in decoded_strings(core.read_json(path))
                           for needle in forbidden if needle in text})
            return not hits, 'Decoded forbidden strings: ' + ', '.join(hits) if hits else 'Decoded strings contain no configured forbidden markers'
        check('DECODED_FORBIDDEN_TEXT', cfg['path'], no_decoded_marker)
    return {'schema': rules['schema'], 'case_id': case_id,
            'rule_sha256': core.sha256(RULE_FILE), 'legacy_source_sha256': core.sha256(Path(core.__file__)),
            'disabled_rules': sorted(disabled), 'legacy_artifact_result': legacy, 'validity_guards': guards,
            'accepted': legacy['all_checks_passed'] and all(g['passed'] for g in guards),
            'new_weighted_score': None,
            'limits': 'Artifact acceptance only. Not product-run evidence, budget success, or Harness causal responsibility.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--outputs', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(adjudicate(args.case, args.outputs), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
