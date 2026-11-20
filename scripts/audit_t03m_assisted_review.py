"""Recheck the C01/C06 dispute in the declared Git snapshot and two mutated copies."""
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
PIN = 'a6bb1d21d3d93535b32636c04a6473631757f835'
OUTPUTS = 'public/week5/pilot-codex-T03-M-r1/outputs'
RECEIPT = ROOT / 'public/behavior-formal/t03m-assisted-review-2026-11-21.json'
ITEMS = ('T03M-C01', 'T03M-C06')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def snapshot(destination, *, extra_paths=()):
    archive = subprocess.check_output([
        'git', 'archive', PIN, '--', 'evaluation_v3', 'harness_eval', 'cases/T03-M', 'config',
        'supplements/grader-v3/rules.json', 'supplements/behavior-protocol-v1/protocol.json', OUTPUTS, *extra_paths,
    ], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(destination, filter='data')


def adjudicate(repository, outputs):
    raw = subprocess.check_output([sys.executable, '-B', '-X', 'utf8', '-m', 'evaluation_v3.grader',
                                   '--case', 'T03-M', '--outputs', str(outputs)], cwd=repository)
    result = json.loads(raw)['legacy_artifact_result']
    checks = {check['id']: {key: check[key] for key in ('path', 'passed', 'reason', 'sha256')}
              for check in result['checks'] if check['id'] in ITEMS}
    return {'score': result['objective_score'], 'selected_checks': checks}


def replace_once(path, old, new):
    data = path.read_bytes()
    if data.count(old) != 1:
        raise ValueError(f'{path.name}: expected one occurrence of the disputed token')
    path.write_bytes(data.replace(old, new, 1))


def price_of(path, product):
    return next(row['price_cents'] for row in read(path)['products'] if row['id'] == product)


def reproduce(repository):
    snapshot(repository)
    actual = repository / OUTPUTS
    case = repository / 'cases/T03-M'
    directive = next(row for row in read(case / 'inputs/release_directive.json')['price_change']
                     if row['product_id'] == 'P-B')
    decision = next(row for row in read(actual / 'steps/01_parsed_directive.json')['excluded_price_changes']
                    if row['product_id'] == 'P-B')
    publication = actual / 'bundle/announcement.md'
    headline = next(line for line in publication.read_text(encoding='utf-8-sig').splitlines() if line.startswith('$1'))
    history = adjudicate(repository, actual)
    counterfactuals = {}
    replacements = {'c01_reason_only': ('steps/01_parsed_directive.json', b'status=draft_do_not_apply', b'draft_do_not_apply'),
                    'c06_label_only': ('bundle/announcement.md', b'$1', '正式发布：'.encode('utf-8'))}
    for name, (relative, before, after) in replacements.items():
        altered = repository / name
        shutil.copytree(actual, altered)
        replace_once(altered / relative, before, after)
        counterfactuals[name] = adjudicate(repository, altered)
    return {'reviewed_commit': PIN, 'historical_artifact_result': history,
            'p_b': {'input_price_cents': price_of(case / 'inputs/catalog.json', 'P-B'),
                    'draft_price_cents': directive['new_value'],
                    'delivered_price_cents': price_of(actual / 'bundle/catalog.json', 'P-B'),
                    'raw_status': directive['status'], 'delivered_reason': decision['reason']},
            'delivered_release_line': headline, 'synthetic_controls': counterfactuals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='tx-t03m-review-') as tmp:
        evidence = reproduce(Path(tmp))
    if args.check and evidence != read(RECEIPT):
        raise ValueError('Published assistant review receipt differs from the pinned recheck.')
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
