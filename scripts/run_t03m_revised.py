"""Run the single preregistered revised T03-M task using the native Codex CLI."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from tempfile import TemporaryDirectory

from run_codex_pilot import ROOT, command, copy_outputs, native_codex, now, run_stage, safe_env
from behavior_codex_access import probe
from audit_t03m_assisted_review import PIN as GRADER_COMMIT, snapshot
from harness_eval.core import inventory, read_json, sha256, write_json


REVISION = 'supplements/t03m-prompt-review-v1'
REGISTER = f'{REVISION}/formal-run-registration.json'
CASE = ROOT / 'cases/T03-M'
RUN_ID = 'product_default-codex-T03-M-r3'
REVIEW = 'reports/behavior-formal/review/T03-M-old-blind-2026-11-21.json'
RULE_REVIEW = 'reports/behavior-formal/review/T03-M-independent-rule-review-2026-11-21.md'
SOURCES = ('evaluation_v3', 'harness_eval', 'config', 'cases/T03-M',
           'supplements/grader-v3/rules.json', 'supplements/behavior-protocol-v1/protocol.json')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def check_registered(commit):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Use the full prospective registration commit.')
    git('merge-base', '--is-ancestor', commit, 'HEAD')
    for name in (REGISTER, REVIEW, RULE_REVIEW, f'{REVISION}/freeze.md', f'{REVISION}/prompt.md',
                 'scripts/run_t03m_revised.py', 'scripts/run_codex_pilot.py',
                 'scripts/behavior_codex_access.py', 'scripts/audit_t03m_assisted_review.py'):
        if git('show', f'{commit}:{name}') != (ROOT / name).read_bytes():
            raise ValueError(f'Working file differs from preregistration: {name}')
    plan = read_json(ROOT / REGISTER)
    if (plan['registration_kind'], plan['run_id'], plan['grader_commit'], plan['attempt']) != (
            'prospective', RUN_ID, GRADER_COMMIT, 1):
        raise ValueError('Wrong revised T03-M registration.')
    if git('show', f"{plan['prompt_source_commit']}:{REVISION}/prompt.md") != (ROOT / REVISION / 'prompt.md').read_bytes():
        raise ValueError('Revision does not match the approved prompt bytes.')
    for name, expected in plan['review_sha256'].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f'Review no longer matches registration: {name}')
    review = read_json(ROOT / REVIEW)
    if (review['reviewed_commit'] != GRADER_COMMIT
            or review['participated_in_grader_implementation'] is not False
            or review['saw_reference_or_machine_score_before_judgment'] is not False
            or set(review['checks']) != {'T03M-C01', 'T03M-C06'}
            or any(not check['blind_basis'] or type(check['recomputed_passed']) is not bool
                   for check in review['checks'].values())):
        raise ValueError('The independent historical blind judgment and recomputation are required.')
    git('diff', '--quiet', GRADER_COMMIT, '--', *SOURCES)
    return plan


def grade(outputs):
    with TemporaryDirectory(prefix='tx-t03m-approved-grader-') as directory:
        snapshot(Path(directory))
        return json.loads(subprocess.check_output([sys.executable, '-B', '-X', 'utf8', '-m',
            'evaluation_v3.grader', '--case', 'T03-M', '--outputs', str(outputs.resolve())], cwd=directory))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-commit', required=True)
    args = parser.parse_args()
    plan = check_registered(args.registration_commit)
    executable = native_codex()
    sha = sha256(executable)
    version = subprocess.check_output([str(executable), '--version'], env=safe_env(), timeout=30).decode().strip()
    if (version, sha) != (plan['cli_version'], plan['cli_binary_sha256']):
        raise ValueError('Installed native CLI differs from the preregistration.')
    login = subprocess.run([str(executable), 'login', 'status'], capture_output=True, env=safe_env(), timeout=30)
    if login.returncode:
        raise ValueError('Native Codex CLI login is unavailable.')

    logs = ROOT / 'private' / RUN_ID
    workspace = ROOT.parent / 'tx-harness-participants' / RUN_ID
    if logs.exists() or workspace.exists():
        raise ValueError('The registered slot has already been prepared.')
    logs.mkdir()
    workspace.mkdir(parents=True)
    record = {'run_id': RUN_ID, 'registration_commit': args.registration_commit,
              'started_at': now(), 'submitted': False, 'tool_qualification_passed': False,
              'cli_version': version, 'cli_binary_sha256': sha, 'status': 'pre_submission_failure'}
    try:
        shutil.copytree(CASE / 'inputs', workspace / 'inputs')
        shutil.copyfile(ROOT / REVISION / 'prompt.md', workspace / 'prompt.md')
        (workspace / 'outputs').mkdir()
        if inventory(workspace) != plan['participant_hashes']:
            raise ValueError('Participant tree differs from the approved prompt and frozen inputs.')

        invocation = command(executable, workspace, None)
        receipt = probe(executable, invocation, workspace, plan['participant_hashes'], 'T03-M', logs, safe_env())
        if inventory(workspace) != plan['participant_hashes'] or next((workspace / 'outputs').iterdir(), None) is not None:
            raise ValueError('Native access check changed the prepared workspace.')
        record.update(tool_qualification_passed=True, access_ended_at=receipt['ended_at'])
        print('Native preflight passed: five inputs and revised prompt readable, four scoring files denied.', flush=True)

        # Preserve the approved prompt and the existing adapter's already disclosed delivery convention.
        from run_codex_pilot import DELIVERY_SUFFIX
        prompt = (workspace / 'prompt.md').read_bytes() + b'\n' + (DELIVERY_SUFFIX + '\n').encode('utf-8')
        (logs / 'submitted-prompt.md').write_bytes(prompt)
        record['submitted_prompt_sha256'] = sha256(logs / 'submitted-prompt.md')
        clock = time.monotonic()
        budget = plan['task_budget_seconds']
        record['status'] = 'capture_failure'
        result = run_stage(invocation, prompt.decode('utf-8'), workspace, logs,
                           'initial', clock, clock + budget)
        record['submitted'] = True
        record['native_turn'] = result
        events = [row['event'] for row in read_json(logs / 'initial.observed.json')]
        record['native_completed'] = any(event['type'] == 'turn.completed' for event in events)
        collected = logs / 'outputs'
        collected.mkdir()
        case = read_json(CASE / 'case.json')
        collection = copy_outputs(case, workspace, collected, time.time() - (time.monotonic() - clock) + budget)
        record.update(collection=collection, input_hashes_after={
            name: sha256(workspace / name) for name in plan['participant_hashes']})
        if record['input_hashes_after'] != plan['participant_hashes']:
            raise ValueError('A participant input was modified.')
        record['status'] = 'timeout' if result['timed_out'] else 'failed'
        if (record['native_completed'] and result['exit_code'] == 0 and not result['timed_out']
                and len(collection['collected']) == len(case['required_outputs'])):
            record['status'] = 'completed'
        write_json(logs / 'score.json', grade(collected))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        write_json(logs / 'error.json', {'type': type(error).__name__, 'message': str(error)})
        print(f'Run stopped: {type(error).__name__}: {error}', file=sys.stderr)
    finally:
        record['ended_at'] = now()
        write_json(logs / 'observation.json', record)
    print(json.dumps({key: record[key] for key in ('run_id', 'status', 'submitted')}, ensure_ascii=False))
    return 0 if (logs / 'score.json').is_file() and record['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
