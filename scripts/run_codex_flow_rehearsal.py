"""Run one registered Codex workflow rehearsal in an external workspace."""
import argparse
from pathlib import Path
import subprocess

from run_codex_pilot import ROOT, command, inventory, native_access_probe, native_codex, now, safe_env
from run_transfer_cli import codex, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-commit', required=True)
    options = parser.parse_args()
    run_id = 'codex-flow-rehearsal-20261121-r1'
    fixture = Path('supplements/codex-flow-rehearsal-v1')
    for name in ('protocol.md', 'prompt.md', 'transactions.csv'):
        source = fixture / name
        frozen = subprocess.check_output(
            ['git', 'show', f'{options.registration_commit}:{source.as_posix()}'], cwd=ROOT)
        if (ROOT / source).read_bytes() != frozen:
            raise ValueError(f'Registered bytes differ: {name}')

    workspace = ROOT.parent / 'tx-harness-participants' / run_id
    evidence = ROOT / 'private' / run_id
    if workspace.exists() or evidence.exists():
        raise ValueError('Rehearsal requires a fresh workspace and evidence directory.')
    (workspace / 'inputs').mkdir(parents=True)
    (workspace / 'outputs').mkdir()
    evidence.mkdir(parents=True)
    for name, target in [('prompt.md', 'prompt.md'), ('transactions.csv', 'inputs/transactions.csv')]:
        (workspace / target).write_bytes((ROOT / fixture / name).read_bytes())
    expected = inventory(workspace)
    executable = native_codex()
    args = command(executable, workspace, None)
    record = {'run_id': run_id, 'registration_commit': options.registration_commit, 'started_at': now(),
              'mode': 'engineering_rehearsal', 'accepted': False, 'completed': False}
    try:
        native_access_probe(executable, args, workspace, expected, 'T03-M', evidence, safe_env())
        if inventory(workspace) != expected or next((workspace / 'outputs').iterdir(), None) is not None:
            raise ValueError('Participant workspace changed after admission.')
        record['native_access_receipt_sha256'] = sha256(evidence / 'access.json')
        prompt = (workspace / 'prompt.md').read_text(encoding='utf-8')
        codex(workspace, evidence, prompt, record)
    finally:
        record['ended_at'] = now()
        artifact = workspace / 'outputs/summary.json'
        record['artifact_sha256'] = sha256(artifact) if artifact.is_file() else None
        write_json(evidence / 'operator.json', record)
    print(f"{run_id}: accepted={record['accepted']}, completed={record['completed']}, file={artifact.is_file()}")


if __name__ == '__main__':
    main()
