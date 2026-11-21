"""Run one preregistered DSH settlement case with a sealed scoring directory."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from run_codex_pilot import ROOT, now, safe_env, stop_tree
from run_dsh_sdk_pilot import SdkPeer
from windows_low_integrity import set_mandatory_label


CASE = 'supplements/dsh-settlement-v1'
DELIVERABLES = ('ledger.csv', 'rejects.csv', 'summary.json')


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def verified_plan(commit):
    path = f'{CASE}/registration.json'
    registered = subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)
    if (ROOT / path).read_bytes() != registered:
        raise ValueError('Manifest differs from registration.')
    plan = json.loads(registered)
    for item, expected in plan['participant_hashes'].items():
        if digest(ROOT / CASE / item) != expected:
            raise ValueError(f'Participant source differs from registration: {item}')
    relative = f'{CASE}/protocol.md'
    if (ROOT / relative).read_bytes() != subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=ROOT):
        raise ValueError('Protocol differs from registration.')
    return plan


def qualify(workspace, vault, plan, launcher, logs):
    expected_inputs = plan['participant_hashes']
    receipts = {}
    for item, (asset, expected_asset) in zip(expected_inputs, plan['asset_hashes'].items(), strict=True):
        protected = vault / asset
        if digest(protected) != expected_asset:
            raise ValueError(f'Evaluator asset unavailable or changed: {asset}')
        proc = subprocess.run([*launcher, *launcher, '--probe', str(workspace / item), str(protected)], cwd=workspace,
                              input=b'', capture_output=True, timeout=30)
        (logs / f'probe-{asset}.stdout.jsonl').write_bytes(proc.stdout)
        (logs / f'probe-{asset}.stderr.txt').write_bytes(proc.stderr)
        if proc.returncode:
            raise ValueError(f'Windows preflight process for {asset} exited {proc.returncode}.')
        observation = json.loads(proc.stdout)
        if observation != {'integrity_rid': 4096, 'input_sha256': expected_inputs[item], 'protected_open_win32': 5}:
            raise ValueError(f'Input or scoring access did not match the frozen rule: {asset}')
        receipts[asset] = {'input': item, **observation, 'evaluator_asset_sha256': expected_asset,
                           'normal_open_verified': True, 'stdout_sha256': sha256(proc.stdout).hexdigest()}
    if next((workspace / 'outputs').iterdir(), None) is not None:
        raise ValueError('Workspace output directory is not empty after qualification.')
    write(logs / 'access.json', receipts)
    return receipts


def submit(workspace, logs, launcher, plan, receipt):
    install = Path(os.environ['LOCALAPPDATA']) / 'Programs/DeepSeek Harness'
    exe = install / 'DeepSeek Harness.exe'
    cli = install / 'resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js'
    patch = workspace / 'dsh-patch.json'
    write(patch, [{'id': 'tool-web', 'disabled': True}, {'id': 'skill-filesystem', 'config': {
        'includeDefaultRoots': False, 'watch': False,
        'bundledSkillDir': (install / 'resources/runtime/office-skills').as_posix()}}])
    env = {**safe_env(), 'ELECTRON_RUN_AS_NODE': '1', 'DSH_PERMISSION_MODE': 'workspace-write',
           'TEMP': str(workspace / 'temp'), 'TMP': str(workspace / 'temp'),
           'DSH_HOME': str(workspace / 'dsh-state'), 'DSH_AGENTS_HOME': str(workspace / 'agent-state')}
    args = [*launcher, str(exe), '--expose-internals', str(cli), '--patch', str(patch), '--profile', 'sdk']
    receipt.update(executable_sha256=digest(exe), config_sha256=digest(patch))
    proc = subprocess.Popen(args, cwd=workspace, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    peer = SdkPeer(proc, logs, plan['run_id'])
    try:
        request, _ = peer.send('initialize', {'cwd': str(workspace), 'provider': plan['sdk_provider_request'],
                                             'model': plan['sdk_model_request'], 'reasoningEffort': 'high'})
        peer.response(request, time.monotonic() + 25)
        # The Windows launcher checks the actual child token before resuming it.
        receipt['token_checked_by_launcher'] = True
        deadline = time.monotonic() + plan['task_budget_seconds']
        prompt = (workspace / 'prompt.md').read_text(encoding='utf-8')
        request, submitted_at = peer.send('session/prompt', {'sessionId': plan['run_id'],
                                                            'contentBlocks': [{'type': 'text', 'text': prompt}]})
        receipt['submitted_at'] = submitted_at
        peer.response(request, deadline)
        receipt['accepted'] = True
        request, _ = peer.send('session/wait', {'sessionId': plan['run_id']})
        peer.response(request, deadline)
        receipt['turn_ends'] = peer.ends
        receipt['completed'] = any(row['reason'] == {'kind': 'completed'} for row in peer.ends)
        if peer.texts:
            receipt['final_reply'] = list(peer.texts.values())[-1]['event']['text']
        request, _ = peer.send('shutdown', {})
        peer.response(request, time.monotonic() + 10)
        proc.stdin.close()
        receipt['exit_code'] = proc.wait(timeout=10)
    finally:
        stop_tree(proc)
        peer.close_logs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-commit', required=True)
    parser.add_argument('--vault', type=Path, required=True)
    args = parser.parse_args()
    plan = verified_plan(args.registration_commit)
    logs = ROOT / 'private' / plan['run_id']
    logs.mkdir(exist_ok=False)
    workspace = Path(tempfile.mkdtemp(prefix='tx-dsh-settlement-')) / 'participant'
    workspace.mkdir()
    record = {'run_id': plan['run_id'], 'registration_commit': args.registration_commit, 'started_at': now(),
              'accepted': False, 'completed': False, 'isolated_preflight_pass': False}
    try:
        set_mandatory_label(workspace, 'S:(ML;OICI;NW;;;LW)')
        for name in ('inputs', 'outputs', 'temp', 'dsh-state', 'agent-state'):
            (workspace / name).mkdir()
        for name in plan['participant_hashes']:
            shutil.copyfile(ROOT / CASE / name, workspace / name)
        helper = [sys.executable, str(ROOT / 'scripts/windows_low_integrity.py')]
        qualify(workspace, args.vault, plan, helper, logs)
        record['isolated_preflight_pass'] = True
        print('Low-integrity preflight: four exact input hashes, four real scoring access denials.', flush=True)
        submit(workspace, logs, helper, plan, record)
        record['participant_hashes_after'] = {key: digest(workspace / key) for key in plan['participant_hashes']}
        collected = logs / 'outputs'
        collected.mkdir()
        record['outputs'] = {}
        for name in DELIVERABLES:
            source = workspace / 'outputs' / name
            if source.is_file() and not source.is_symlink():
                shutil.copyfile(source, collected / name)
                record['outputs'][name] = digest(collected / name)
        if record['completed'] and record['participant_hashes_after'] == plan['participant_hashes']:
            grade = subprocess.check_output([sys.executable, '-B', str(args.vault / 'grader.py'),
                                             '--outputs', str(collected)], cwd=logs)
            write(logs / 'score.json', json.loads(grade))
    except Exception as error:
        record['runtime_error_type'] = type(error).__name__
        write(logs / 'error.json', {'message': str(error)})
    finally:
        record['ended_at'] = now()
        write(logs / 'observation.json', record)
    print({key: record.get(key) for key in ('accepted', 'completed', 'outputs', 'runtime_error_type')})
    return 0 if (logs / 'score.json').is_file() else 1


if __name__ == '__main__':
    raise SystemExit(main())
