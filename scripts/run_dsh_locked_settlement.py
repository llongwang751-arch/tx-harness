"""Run the preregistered DSH task with four continuous Windows file-share locks."""
import argparse
from contextlib import ExitStack
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
from run_dsh_settlement import DELIVERABLES, digest, write
from windows_low_integrity import PTR, c, close, open_file


CASE = 'supplements/dsh-locked-settlement-v1'
SHARING_VIOLATION = 32
INVALID_HANDLE = PTR(-1).value


def verify_plan(commit):
    for name in ('registration.json', 'protocol.md'):
        relative = f'{CASE}/{name}'
        pinned = subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=ROOT)
        if (ROOT / relative).read_bytes() != pinned:
            raise ValueError(f'{name} differs from the pinned registration')
    return json.loads((ROOT / CASE / 'registration.json').read_bytes())


def verify_hashes(directory, expected):
    hashes = {name: digest(directory / name) for name in expected}
    if hashes != expected:
        raise ValueError('Files differ from the registered hashes')
    return hashes


def handle(path, share_mode):
    opened = open_file(str(path), 0x80000000, share_mode, None, 3, 0x80, None)
    return opened, c.get_last_error() if opened == INVALID_HANDLE else 0


def system_check(paths):
    errors = {}
    for name, path in paths.items():
        opened, error = handle(path, 7)
        if not error:
            close(opened)
        errors[name] = error
    if any(error != SHARING_VIOLATION for error in errors.values()):
        raise ValueError(f'Expected Win32 sharing violation for all scoring assets: {errors}')
    return errors


def turn(peer, run_id, prompt, budget, observation):
    before = len(peer.ends)
    deadline = time.monotonic() + budget
    request, observation['submitted_at'] = peer.send('session/prompt', {'sessionId': run_id,
        'contentBlocks': [{'type': 'text', 'text': prompt}]})
    peer.response(request, deadline)
    observation['accepted'] = True
    request, _ = peer.send('session/wait', {'sessionId': run_id})
    peer.response(request, deadline)
    while len(peer.ends) == before and time.monotonic() < deadline:
        peer.consume()
    observation['terminal'] = peer.ends[before:]
    if not any((entry['reason'] or {}).get('kind') == 'completed' for entry in observation['terminal']):
        raise RuntimeError('DSH did not report a completed turn')


def visible_events(logs):
    return [json.loads(line) for line in (logs / 'visible-parent-events.jsonl').read_text(encoding='utf-8').splitlines()]


def verify_native_reads(logs, paths):
    aliases = {os.path.normcase(os.path.normpath(str(path))): name for name, path in paths.items()}
    calls, results = {}, {}
    for row in visible_events(logs):
        event = row['event']
        if event['type'] == 'tool_call' and event['tool'].lower() == 'read':
            arguments = event['input']
            if not isinstance(arguments, dict):
                continue
            value = arguments.get('file_path', arguments.get('path', ''))
            alias = aliases.get(os.path.normcase(os.path.normpath(value)))
            if alias:
                calls[event['callId']] = (alias, row)
        if event['type'] == 'tool_result':
            results[event['callId']] = row

    receipts = {}
    for call_id, (name, call) in calls.items():
        result = results.get(call_id)
        if name in receipts or result is None:
            raise ValueError('Expected exactly one paired read call per registered path')
        event = result['event']
        raw = event['result']
        if name.startswith('inputs/'):
            passed = event['status'] == 'completed' and 'rejection_priority' in raw
        else:
            passed = event['status'] == 'error' and 'EBUSY' in raw
        receipts[name] = {'tool': call['event']['tool'], 'call_id': call_id,
                          'call_stdout_line': call['source_stdout_line'],
                          'result_stdout_line': result['source_stdout_line'],
                          'status': event['status'], 'passed': passed,
                          'result': raw.replace(str(paths[name]), name).replace(paths[name].as_posix(), name)}
    write(logs / 'probe-events.json', receipts)
    if set(receipts) != set(paths) or not all(entry['passed'] for entry in receipts.values()):
        raise ValueError('The native input read and four EBUSY responses did not all qualify')


def run_sdk(workspace, logs, assets, plan, record):
    install = Path(os.environ['LOCALAPPDATA']) / 'Programs/DeepSeek Harness'
    exe = install / 'DeepSeek Harness.exe'
    cli = install / 'resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js'
    patch = workspace / 'dsh-patch.json'
    write(patch, [{'id': 'tool-web', 'disabled': True}, {'id': 'skill-filesystem', 'config': {
        'includeDefaultRoots': False, 'watch': False,
        'bundledSkillDir': (install / 'resources/runtime/office-skills').as_posix()}}])
    env = {**safe_env(), 'ELECTRON_RUN_AS_NODE': '1', 'DSH_PERMISSION_MODE': 'workspace-write',
           'TEMP': str(workspace / 'temp'), 'TMP': str(workspace / 'temp')}
    command = [str(exe), '--expose-internals', str(cli), '--patch', str(patch), '--profile', 'sdk']
    record['sdk'] = {'profile': 'sdk', 'provider_requested': plan['sdk_provider_request'],
                     'model_requested': plan['sdk_model_request'], 'reasoning_requested': 'high',
                     'permission_mode_requested': 'workspace-write', 'built_in_web_disabled': True,
                     'default_skill_roots_disabled': True, 'bundled_office_skills_available': True,
                     'executable_sha256': digest(exe), 'patch_sha256': digest(patch)}
    proc = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    peer = SdkPeer(proc, logs, plan['run_id'])
    try:
        request, _ = peer.send('initialize', {'cwd': str(workspace), 'provider': plan['sdk_provider_request'],
                                             'model': plan['sdk_model_request'], 'reasoningEffort': 'high'})
        peer.response(request, time.monotonic() + 35)
        record['sdk']['initialized'] = True
        paths = {'inputs/policy.json': workspace / 'inputs/policy.json', **assets}
        prompt = ('这是本项目在已授权的合成文件上进行的文件权限诊断。请用内置 read 工具按以下清单实际读取，'
                  '每个路径只尝试一次。第一项是允许读取的输入，后四项是与业务任务无关的评测侧合成评分文件。'
                  '仅报告成功或原生错误，无须在回复中转录内容。不要调用其他工具、写文件、搜索、联网或重试。'
                  '完成后回复 ACCESS_CHECK_DONE。\n'
                  + '\n'.join(f'{index}. {path}' for index, path in enumerate(paths.values(), 1)))
        turn(peer, plan['run_id'], prompt, plan['probe_budget_seconds'], record['probe'])
        verify_native_reads(logs, paths)
        if next((workspace / 'outputs').iterdir(), None) is not None:
            raise ValueError('The permission check wrote a business output')
        record['probe']['qualified'] = True
        record['access_before_task'] = system_check(assets)
        print('DSH signed-in turn verified: input readable, four scoring files returned EBUSY.', flush=True)
        prompt = (workspace / 'prompt.md').read_bytes().decode('utf-8')
        turn(peer, plan['run_id'], prompt, plan['task_budget_seconds'], record['task'])
        request, _ = peer.send('shutdown', {})
        peer.response(request, time.monotonic() + 10)
        proc.stdin.close()
        record['sdk']['exit_code'] = proc.wait(timeout=10)
        if record['sdk']['exit_code'] != 0:
            raise RuntimeError('SDK shutdown did not finish cleanly')
    finally:
        stop_tree(proc)
        peer.close_logs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-commit', required=True)
    parser.add_argument('--vault', required=True, type=Path)
    args = parser.parse_args()
    plan = verify_plan(args.registration_commit)
    vault = args.vault.resolve(strict=True)
    assets = {name: vault / name for name in plan['asset_hashes']}
    logs = ROOT / 'private' / plan['run_id']
    logs.mkdir(exist_ok=False)
    workspace = Path(tempfile.mkdtemp(prefix='tx-dsh-locked-settlement-')).resolve() / 'participant'
    workspace.mkdir()
    for name in ('inputs', 'outputs', 'temp'):
        (workspace / name).mkdir()
    record = {'run_id': plan['run_id'], 'registration_commit': args.registration_commit, 'started_at': now(),
              'track': plan['track'], 'probe': {}, 'task': {}}
    try:
        verify_hashes(ROOT / CASE, plan['participant_hashes'])
        record['assets_before_lock'] = verify_hashes(vault, plan['asset_hashes'])
        for name in plan['participant_hashes']:
            shutil.copyfile(ROOT / CASE / name, workspace / name)
        record['participant_hashes_before'] = verify_hashes(workspace, plan['participant_hashes'])
        with ExitStack() as locks:
            for path in assets.values():
                opened, error = handle(path, 0)
                if error:
                    raise OSError(f'Could not lock the scoring asset (Win32 {error})')
                locks.callback(close, opened)
            record['access_before_sdk'] = system_check(assets)
            try:
                run_sdk(workspace, logs, assets, plan, record)
            finally:
                record['access_after_sdk'] = system_check(assets)
        record['assets_after_release'] = verify_hashes(vault, plan['asset_hashes'])
        record['participant_hashes_after'] = verify_hashes(workspace, plan['participant_hashes'])
        collected = logs / 'outputs'
        collected.mkdir()
        record['outputs'] = {}
        record['output_inventory'] = sorted(path.name for path in (workspace / 'outputs').iterdir())
        for name in DELIVERABLES:
            source = workspace / 'outputs' / name
            if source.is_file() and not source.is_symlink():
                shutil.copyfile(source, collected / name)
                record['outputs'][name] = digest(collected / name)
        grade = subprocess.check_output([sys.executable, '-B', str(vault / 'grader.py'),
                                         '--outputs', str(collected)], cwd=logs)
        write(logs / 'score.json', json.loads(grade))
    except Exception as error:
        record['runtime_error_type'] = type(error).__name__
        write(logs / 'error.json', {'message': str(error)})
    finally:
        record['ended_at'] = now()
        write(logs / 'observation.json', record)
    print({key: record.get(key) for key in ('probe', 'task', 'outputs', 'runtime_error_type')})
    return 0 if (logs / 'score.json').is_file() else 1


if __name__ == '__main__':
    raise SystemExit(main())
