"""Verify the new pair without changing historical data or trusting product prose."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.window_reopen import judge

BASE = ROOT / 'public/supplements/window-reopen-v1'
PROTOCOL = 'supplements/window-reopen-v1/protocol.json'
REGISTRATION = 'c6d3215523ec75dbe4bae009d9474c04aab6108f'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_timing(directory, execution, seal, protocol):
    start = datetime.fromisoformat(execution['started_at'])
    end = datetime.fromisoformat(seal['at'])
    assert start.tzinfo and end.tzinfo
    assert abs((end-start).total_seconds()*1000-seal['elapsed_ms']) < 1000
    checkpoint = read(directory / 'checkpoint.json')
    continuation = read(directory / 'continuation.json')
    before = datetime.fromisoformat(continuation['before_at'])
    after = datetime.fromisoformat(continuation['after_at'])
    checkpoint_at = datetime.fromisoformat(checkpoint['at'])
    assert start <= checkpoint_at < before <= after <= end
    observed_delay = (before-checkpoint_at).total_seconds()
    assert abs(observed_delay-continuation['delay_seconds']) < 1
    assert abs(observed_delay-protocol['checkpoint_delay_seconds']) <= protocol['delay_tolerance_seconds']
    return start, end


def check_custody(directory, seal, run, start, end):
    middle = 'stage-a-after-reopen' if run.endswith('window-reopen') else 'stage-a-after-wait'
    expected = {'stage-a/stage-a.txt', middle+'/stage-a.txt',
                'stage-b/stage-a.txt', 'stage-b/stage-b.txt', 'stage-b/receipt.json'}
    rows = seal['inventory']
    journal = [json.loads(line) for line in (directory / 'collection.jsonl').read_text(encoding='utf-8').splitlines()]
    assert journal == rows, 'Seal does not bind the acquisition journal'
    names = [row['collected'].split('/collected/', 1)[1] for row in rows]
    assert len(names) == len(set(names)) and set(names) == expected, 'Seal must cover each original acquisition exactly once'
    actual = {p.relative_to(directory / 'collected').as_posix() for p in (directory / 'collected').rglob('*') if p.is_file()}
    assert actual == expected
    for row, name in zip(rows, names):
        assert 0 <= row['elapsed_ms'] <= seal['elapsed_ms'] <= 1200000
        acquired = datetime.fromisoformat(row['at'])
        assert start <= acquired <= end
        assert abs((acquired-start).total_seconds()*1000-row['elapsed_ms']) < 1000
        path = directory / 'collected' / name
        assert path.is_file() and digest(path) == row['sha256'] and path.stat().st_size == row['bytes']


def verify():
    index = read(BASE / 'index.json')
    registration = index['registration_commit']
    assert registration == REGISTRATION, 'Unexpected preregistration commit'
    registered_at = datetime.fromisoformat(subprocess.check_output(
        ['git', 'show', '-s', '--format=%cI', registration], cwd=ROOT, text=True).strip())
    registered = subprocess.check_output(['git', 'show', f'{registration}:{PROTOCOL}'], cwd=ROOT)
    assert registered == (ROOT / PROTOCOL).read_bytes(), 'Registered protocol changed'
    protocol = read(ROOT / PROTOCOL)
    for name, spec in protocol['files'].items():
        path = ROOT / name
        assert path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256'], name
        assert subprocess.check_output(['git', 'show', f'{registration}:{name}'], cwd=ROOT) == path.read_bytes(), name
    assert index['runs'] == protocol['order']
    results = []
    for run in index['runs']:
        directory = BASE / run
        manifest = read(directory / 'manifest.json')
        assert manifest['run_id'] == run
        listed = set(manifest['files'])
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        assert actual == listed, 'Package file inventory differs'
        for name, spec in manifest['files'].items():
            path = directory / name
            assert path.resolve().is_relative_to(directory.resolve())
            assert path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256'], name
        execution = read(directory / 'execution.json')
        assert execution['registration_commit'] == registration
        assert execution['actual_submitted'] is True and execution['run_id'] == run
        assert execution['input_sha256'] == protocol['files']['supplements/window-reopen-v1/fixtures/p1/probe.txt']['sha256']
        assert execution['prompt_sha256'] == protocol['files']['supplements/window-reopen-v1/fixtures/p1/prompt.txt']['sha256']
        for source in execution['evidence']:
            assert (directory / source).is_file(), source
        seal = read(directory / 'seal.json')
        assert seal['within_budget'] and 0 <= seal['elapsed_ms'] <= protocol['run_budget_seconds']*1000
        start, end = check_timing(directory, execution, seal, protocol)
        assert registered_at <= start, 'Protocol commit must precede submission'
        check_custody(directory, seal, run, start, end)
        actual_judgment = judge((ROOT / 'supplements/window-reopen-v1/fixtures/p1/probe.txt').read_bytes(), directory / 'outputs')
        assert actual_judgment == read(directory / 'judgment.json')
        assert execution['artifact_outcome'] == ('pass' if actual_judgment['joint_delivery_pass'] else 'fail')
        for name in ('stage-a.txt', 'stage-b.txt', 'receipt.json'):
            assert (directory / 'outputs' / name).read_bytes() == (directory / 'collected/stage-b' / name).read_bytes()
        if run.endswith('window-reopen'):
            intervention = read(directory / 'intervention.json')
            assert intervention['restored_same_task'] is True
            assert intervention['claim'] == 'window_reopen_only'
            if intervention['verdict'] == 'verified':
                assert intervention['after_close_workbuddy_windows'] == []
                assert execution['validity'] == 'valid'
            else:
                assert intervention['verdict'] == 'unknown'
                assert intervention['protocol_deviation'] and intervention['reason']
                assert execution['validity'] == 'unknown' and execution['outcome'] == 'unknown'
        else:
            assert execution['validity'] == 'valid' and execution['outcome'] == execution['artifact_outcome']
        review = read(directory / 'review.json')
        assert review['rule_version'] == 'window-reopen/v1'
        assert (directory / review['rules']).resolve() == ROOT / PROTOCOL
        assert all((directory / name).is_file() for name in review['inputs'])
        assert review['configuration'] == 'execution.json#/configuration'
        assert review['artifacts'] == 'judgment.json'
        known_unknowns = {item['id'] for item in read(ROOT / 'supplements/week2/unknowns.json')['items']}
        assert set(review['unknown_register']) <= known_unknowns
        for metric in review['metrics'].values():
            assert metric['reason'] and metric['confidence'] and metric['evidence']
            assert metric['status'] in ('pass', 'fail', 'unknown', 'not_applicable')
            assert all((directory / name).is_file() for name in metric['evidence'])
        assert review['metrics']['stage_b_joint_delivery']['status'] == execution['artifact_outcome']
        assert review['metrics']['attachment_stored_bytes']['status'] == 'unknown'
        assert review['metrics']['window_intervention']['status'] == ('unknown' if run.endswith('window-reopen') else 'not_applicable')
        results.append({'run_id': run, 'validity': execution['validity'], 'outcome': execution['outcome'],
                        'joint_delivery_pass': actual_judgment['joint_delivery_pass'],
                        'sealed_within_budget': seal['within_budget']})
    assert index['new_independent_product_runs'] == len(results)
    assert index['known_valid_runs'] == sum(r['validity']=='valid' for r in results)
    assert index['known_passed_runs'] == sum(r['validity']=='valid' and r['outcome']=='pass' for r in results)
    assert index['unknown_runs'] == sum(r['validity']=='unknown' or r['outcome']=='unknown' for r in results)
    assert index['failed_runs'] == sum(r['validity']=='valid' and r['outcome']=='fail' for r in results)
    assert index['artifact_complete_runs'] == sum(r['joint_delivery_pass'] for r in results)
    assert index['pair_validity'] == 'unknown' and index['pair_causal_effect'] == 'not_established'
    print(json.dumps({'verified_runs': results, 'new_independent_product_runs': len(results),
                      'limits': 'Hash/contract/timing consistency; UI provenance remains operator-collected, not independent corroboration.'}))


if __name__ == '__main__':
    verify()
