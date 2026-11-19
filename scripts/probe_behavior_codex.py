"""Run an unscored access check without submitting the business task."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness_eval.core import inside, inventory, load_case, sha256, write_json
from scripts.behavior_codex_access import native_command_observation, probe
from scripts.behavior_preflight import stage_workspace
from scripts.run_codex_pilot import command, native_codex, now, run_stage, safe_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True, help='Fresh diagnostic identifier')
    parser.add_argument('--case', choices=['T03-M', 'T05-M'], default='T03-M')
    parser.add_argument('--codex', help='Absolute path to the native binary')
    parser.add_argument('--native-turn', action='store_true', help='Confirm via one real command tool turn')
    args = parser.parse_args()
    if not args.id.isascii() or not args.id.replace('-', '').isalnum():
        raise ValueError('Use a simple alphanumeric diagnostic ID with hyphens.')
    executable = native_codex(args.codex)
    version = subprocess.check_output([str(executable), '--version'], env=safe_env(), timeout=20).decode().strip()
    case_dir = ROOT / 'cases' / args.case
    task, _ = load_case(case_dir)
    workspace = ROOT.parent / 'tx-harness-participants' / f'access-{args.id}'
    evidence = ROOT / 'private/behavior-access' / args.id

    def create():
        workspace.mkdir(parents=True, exist_ok=False)
        shutil.copytree(inside(case_dir, task['input_dir']), workspace / 'inputs')
        shutil.copyfile(inside(case_dir, task['prompt_file']), workspace / 'prompt.md')
        (workspace / 'outputs').mkdir()

    evidence.mkdir(parents=True, exist_ok=False)
    expected = stage_workspace(case_dir, workspace, create)
    argv = command(executable, workspace, None)
    receipt = probe(executable, argv, workspace, expected, args.case, evidence, safe_env())
    receipt.update(case_id=args.case, diagnostic_id=args.id, codex_version=version, business_task_submitted=False,
                   native_turn=None)
    write_json(evidence / 'summary.json', receipt)
    if args.native_turn:
        files = ','.join(f"'{name}'" for name in sorted(expected))
        prompt = 'Local file-read qualification only. Use the PowerShell shell tool once, running the following command in the current working directory. It hashes only the allowed input files. Do not open any other locations or solve the case.\n'
        prompt += (f"$map = @{{}}; foreach ($file in @({files})) {{ "
                   "$map[$file] = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() "
                   "}; $map | ConvertTo-Json -Compress\n")
        started = time.monotonic()
        result = run_stage(argv, prompt, workspace, evidence, 'native-access', started, started + 140)
        if result['exit_code'] != 0 or result['timed_out']:
            raise ValueError('Native tool confirmation did not finish normally; private streams retained.')
        matched = native_command_observation(evidence / 'native-access.stdout.jsonl', expected)
        if inventory(workspace) != expected or next((workspace / 'outputs').iterdir(), None) is not None:
            raise ValueError('Access-only task changed the prepared workspace.')
        receipt['native_turn'] = {'observed_at': now(), 'exit_code': result['exit_code'],
                                  'started_at': result['submitted_at'], 'ended_at': result['ended_at'],
                                  'native_stream_sha256': sha256(evidence / 'native-access.stdout.jsonl'),
                                  'matched_shell_input_sha256': matched}
        write_json(evidence / 'summary.json', receipt)
    print(f'{version}: {len(expected)} positive file reads, {len(receipt["protected_files"])} access denials. Business submissions: 0.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Access diagnostic failed: {exc}', file=sys.stderr)
        sys.exit(2)
