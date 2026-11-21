"""Verify the sealed settlement evidence and replay near-miss judge controls."""
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'supplements/dsh-settlement-v1'
PUBLIC = ROOT / 'public/settlement-20261121'
ASSETS = PUBLIC / 'grader-assets'
SUCCESS = PUBLIC / 'codex-settlement-20261121-r3'
LOCKED_CASE = ROOT / 'supplements/dsh-locked-settlement-v1'
LOCKED_RUN = ROOT / 'public/dsh-locked-settlement-20261121'


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def grade(outputs):
    raw = subprocess.check_output([sys.executable, '-B', str(ASSETS / 'grader.py'), '--outputs', str(outputs)])
    return json.loads(raw)


def verify_dsh(plan):
    folder = PUBLIC / 'dsh-settlement-20261121-r1'
    record = read(folder / 'observation.json')
    require(record['accepted'] and not record['completed'] and record['isolated_preflight_pass']
            and not record['outputs'], 'DSH authorization stop was misclassified')
    require(read(folder / 'native-end.excerpt.json')['reason']['error']['code'] == 'ACCOUNT_SIGN_IN_REQUIRED',
            'Missing original SDK terminal error')
    receipts = record['access_receipt']
    require(set(receipts) == set(plan['asset_hashes']), 'Unexpected set of DSH protected targets')
    for name, receipt in receipts.items():
        raw = folder / f'probe-{name}.stdout.jsonl'
        observation = {'integrity_rid': 4096, 'input_sha256': plan['participant_hashes'][receipt['input']],
                       'protected_open_win32': 5}
        require(read(raw) == observation and digest(raw) == receipt['stdout_sha256']
                and receipt['evaluator_asset_sha256'] == plan['asset_hashes'][name]
                and receipt['normal_open_verified'], f'DSH access evidence mismatch: {name}')


def verify_codex(plan):
    for number in (1, 2):
        blocked = PUBLIC / f'codex-settlement-20261121-r{number}'
        entry = read(blocked / 'observation.json')
        require(not entry['accepted'] and not entry['isolated_preflight_pass'], f'Preflight stop {number} was counted as a task')
    original_probe = read(PUBLIC / 'codex-settlement-20261121-r2/access.stdout.jsonl')
    require(original_probe['protected_open'] == dict.fromkeys(('grader', 'rubric', 'oracle', 'reference'), 'readable'),
            'The second probe must preserve the four real reads')
    record = read(SUCCESS / 'observation.json')
    require(record['accepted'] and record['completed'] and record['exit_code'] == 0, 'Missing native task completion')
    original = subprocess.check_output(['git', 'show', f"{record['registration_commit']}:supplements/dsh-settlement-v1/registration.json"], cwd=ROOT)
    require(json.loads(original) == plan, 'The successful run did not use the pre-registered plan')
    access = read(SUCCESS / 'access.json')
    raw = SUCCESS / 'access.stdout.jsonl'
    require(access['observation'] == read(raw) and access['stdout_sha256'] == digest(raw)
            and access['asset_hashes'] == plan['asset_hashes'], 'Codex native access receipt is inconsistent')
    require(access['observation']['input_sha256'] == plan['participant_hashes'] == record['participant_hashes_after']
            and access['observation']['protected_open'] == dict.fromkeys(('grader', 'rubric', 'oracle', 'reference'), 'denied:80070005'),
            'Codex did not match the frozen inputs and all four denials')
    require(datetime.fromisoformat(access['completed_at']) < datetime.fromisoformat(record['submitted_at']),
            'Permission proof did not precede the task')
    events = read(SUCCESS / 'native-events.excerpts.json')
    require(events[0]['type'] == 'turn.started' and events[-1]['type'] == 'turn.completed', 'Missing native lifecycle excerpts')
    expected = ('ledger.csv', 'rejects.csv', 'summary.json')
    require(record['outputs'] == {name: digest(SUCCESS / 'outputs' / name) for name in expected},
            'Archived outputs differ from the collected originals')
    return grade(SUCCESS / 'outputs')


def check_near_misses():
    with TemporaryDirectory(prefix='tx-settlement-audit-') as folder:
        archive = Path(folder) / 'outputs'
        shutil.copytree(SUCCESS / 'outputs', archive)
        rejects = archive / 'rejects.csv'
        rows = list(csv.reader(rejects.read_text(encoding='utf-8-sig').splitlines()))
        next(row for row in rows if row[0] == 'O-703')[1] = 'not_settled'
        with rejects.open('w', encoding='utf-8', newline='') as stream:
            csv.writer(stream).writerows(rows)
        priority = grade(archive)
        require(priority['score'] == 80 and not priority['checks']['rejections_and_priority'], 'Judge missed the wrong priority')
        shutil.copyfile(SUCCESS / 'outputs' / 'rejects.csv', rejects)
        summary = read(archive / 'summary.json')
        summary['total_fee_cents'] = str(summary['total_fee_cents'])
        (archive / 'summary.json').write_text(json.dumps(summary), encoding='utf-8')
        wrong_type = grade(archive)
        require(wrong_type['score'] == 65 and not wrong_type['checks']['summary_exact']
                and not wrong_type['checks']['internal_reconciliation'], 'Judge accepted a string total')


def verify_locked_dsh():
    plan = read(LOCKED_CASE / 'registration.json')
    record = read(LOCKED_RUN / 'observation.json')
    require(record['run_id'] == plan['run_id'] and record['track'] == plan['track'],
            'DSH run identity differs from its registration')
    for name in ('registration.json', 'protocol.md'):
        registered = subprocess.check_output(['git', 'show',
            f"{record['registration_commit']}:supplements/dsh-locked-settlement-v1/{name}"], cwd=ROOT)
        require(registered == (LOCKED_CASE / name).read_bytes(), f'DSH registration changed: {name}')
    require(record['assets_before_lock'] == record['assets_after_release'] == plan['asset_hashes']
            == {name: digest(LOCKED_RUN / 'grader-assets' / name) for name in plan['asset_hashes']},
            'DSH scoring-asset hashes differ from the sealed originals')
    require(record['participant_hashes_before'] == record['participant_hashes_after'] == plan['participant_hashes']
            == {name: digest(LOCKED_CASE / name) for name in plan['participant_hashes']},
            'DSH inputs differ from the registered originals')
    for checkpoint in ('access_before_sdk', 'access_before_task', 'access_after_sdk'):
        require(record[checkpoint] == dict.fromkeys(plan['asset_hashes'], 32), f'Wrong Win32 status: {checkpoint}')

    probe, task = record['probe'], record['task']
    require(record['sdk']['initialized'] and record['sdk']['exit_code'] == 0
            and probe['accepted'] and probe['qualified'] and task['accepted'],
            'The signed-in DSH run did not qualify or exit cleanly')
    probe_end, task_end = (entry['terminal'][-1] for entry in (probe, task))
    require(probe_end['reason']['kind'] == task_end['reason']['kind'] == 'completed'
            and datetime.fromisoformat(probe_end['received_at']) < datetime.fromisoformat(task['submitted_at']),
            'DSH did not finish the native access probe before task submission')
    probe_events = read(LOCKED_RUN / 'probe-events.json')
    require(set(probe_events) == {'inputs/policy.json', *plan['asset_hashes']}
            and len({entry['call_id'] for entry in probe_events.values()}) == len(probe_events),
            'Expected five distinct native access attempts')
    for name, entry in probe_events.items():
        status, marker = ('completed', 'rejection_priority') if name == 'inputs/policy.json' else ('error', 'EBUSY')
        require(entry['tool'] == 'read' and entry['status'] == status and marker in entry['result']
                and entry['passed'] and entry['call_stdout_line'] < entry['result_stdout_line'] < probe_end['source_stdout_line'],
                f'Invalid native access event: {name}')

    expected = ('ledger.csv', 'rejects.csv', 'summary.json')
    require(record['outputs'] == {name: digest(LOCKED_RUN / 'outputs' / name) for name in expected}
            and set(record['output_inventory']) == set(expected), 'DSH archived outputs differ from collection')
    events = read(LOCKED_RUN / 'task-events.excerpts.json')
    require(events[0]['event']['phase'] == 'turn_start'
            and events[-1]['event']['phase'] == 'turn_end'
            and events[-1]['source_stdout_line'] == task_end['source_stdout_line'], 'Missing native DSH task lifecycle')
    statuses = {row['event']['callId']: row['event']['status']
                for row in events if row['event']['type'] == 'tool_result'}
    written = {row['event'].get('target') for row in events if row['event'].get('tool') == 'write'
               and statuses.get(row['event']['callId']) == 'completed'}
    require(written == {f'outputs/{name}' for name in expected}, 'Missing successful writes in native DSH events')
    recomputed = subprocess.check_output([sys.executable, '-B', str(LOCKED_RUN / 'grader-assets/grader.py'),
        '--outputs', str(LOCKED_RUN / 'outputs'), '--check'])
    print(f"Signed-in DSH settlement: {json.loads(recomputed)['score']}/100; four native EBUSY denials verified.")


def main():
    plan = read(CASE / 'registration.json')
    for name, expected in plan['asset_hashes'].items():
        require(digest(ASSETS / name) == expected, f'Seal mismatch: {name}')
    for name, expected in plan['participant_hashes'].items():
        require(digest(CASE / name) == expected, f'Stimulus mismatch: {name}')
    verify_dsh(plan)
    score = verify_codex(plan)
    require(score == read(SUCCESS / 'score.json') and score['score'] == score['max_score'] == 100,
            'Published settlement score differs from the sealed grader')
    check_near_misses()
    print('Settlement evidence: Codex 100/100, four post-fix denials, DSH authorization stop and judge controls verified.')
    verify_locked_dsh()


if __name__ == '__main__':
    main()
