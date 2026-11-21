"""Run the same sealed settlement task through the native Codex sandbox."""
import argparse
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from run_codex_pilot import ROOT, command, native_codex, now, safe_env
from behavior_codex_access import program, sandbox_config, validate_observation
from run_dsh_settlement import CASE, DELIVERABLES, digest, verified_plan, write
from run_transfer_cli import codex


def authorize(workspace, vault, logs, plan):
    paths = {path: vault / path for path in plan['asset_hashes']}
    for name, path in paths.items():
        if digest(path) != plan['asset_hashes'][name]:
            raise ValueError(f'Invalid sealed asset: {name}')
    executable = native_codex()
    options = sandbox_config(command(executable, workspace, None))
    config = [part for option in options for part in ('-c', option)]
    shell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    source = program(plan['participant_hashes'], paths)
    script = base64.b64encode(source.encode('utf-16-le')).decode('ascii')
    with tempfile.TemporaryDirectory(prefix='codex-settlement-config-') as home:
        args = [str(executable), 'sandbox', '--cd', str(workspace), '--permission-profile', 'harness_pilot',
                *config, '--', str(shell), '-NoProfile', '-NonInteractive', '-EncodedCommand', script]
        proc = subprocess.run(args, cwd=workspace, env={**safe_env(), 'CODEX_HOME': home},
                              capture_output=True, timeout=35)
    (logs / 'access.stdout.jsonl').write_bytes(proc.stdout)
    (logs / 'access.stderr.txt').write_bytes(proc.stderr)
    if proc.returncode:
        raise ValueError(f'Native Windows access check exited {proc.returncode}.')
    observation = json.loads(proc.stdout)
    validate_observation(observation, plan['participant_hashes'], paths)
    if next((workspace / 'outputs').iterdir(), None) is not None:
        raise ValueError('Workspace is not clean after access check.')
    write(logs / 'access.json', {'observation': observation, 'asset_hashes': plan['asset_hashes'],
                                 'stdout_sha256': sha256(proc.stdout).hexdigest(), 'completed_at': now()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-commit', required=True)
    parser.add_argument('--vault', type=Path, required=True)
    args = parser.parse_args()
    plan = verified_plan(args.registration_commit)
    followup = f'{CASE}/codex-followup.md'
    registered = subprocess.check_output(['git', 'show', f'{args.registration_commit}:{followup}'], cwd=ROOT)
    if registered != (ROOT / followup).read_bytes():
        raise ValueError('Codex follow-up differs from its registration.')
    run_id = 'codex-settlement-20261121-r1'
    workspace = ROOT.parent / 'tx-harness-participants' / run_id
    logs = ROOT / 'private' / run_id
    if workspace.exists() or logs.exists():
        raise ValueError('Run requires a fresh workspace and evidence directory.')
    for folder in (workspace / 'inputs', workspace / 'outputs', logs):
        folder.mkdir(parents=True)
    record = {'run_id': run_id, 'registration_commit': args.registration_commit, 'started_at': now(),
              'accepted': False, 'completed': False, 'isolated_preflight_pass': False}
    try:
        for name in plan['participant_hashes']:
            shutil.copyfile(ROOT / CASE / name, workspace / name)
        authorize(workspace, args.vault, logs, plan)
        record['isolated_preflight_pass'] = True
        print('Codex native preflight: four exact input hashes, four real scoring access denials.', flush=True)
        codex(workspace, logs, (workspace / 'prompt.md').read_text(encoding='utf-8'), record)
        record['participant_hashes_after'] = {key: digest(workspace / key) for key in plan['participant_hashes']}
        collected = logs / 'outputs'
        collected.mkdir()
        record['outputs'] = {}
        for name in DELIVERABLES:
            p = workspace / 'outputs' / name
            if p.is_file() and not p.is_symlink():
                shutil.copyfile(p, collected / name)
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
    import sys
    raise SystemExit(main())
