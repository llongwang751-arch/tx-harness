"""Run the one-shot DSH file-tool and read-only PowerShell diagnostic."""
import argparse
from pathlib import Path
import subprocess

from run_transfer_cli import ROOT, dsh, now, sha256, write_json

RUN_ID = 'diag-20261119-dsh-file-vs-shell-r1'
CASE = Path('supplements/dsh-shell-diagnostic-v1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration-commit', required=True)
    args = parser.parse_args()
    for name in ('protocol.md', 'prompt.txt'):
        path = CASE / name
        registered = subprocess.check_output(
            ['git', 'show', f'{args.registration_commit}:{path.as_posix()}'], cwd=ROOT)
        if registered != (ROOT / path).read_bytes():
            raise ValueError(f'Registered bytes differ: {path}')

    work = ROOT.parent / 'tx-harness-participants' / RUN_ID
    evidence = ROOT / 'private' / RUN_ID
    if evidence.exists() or work.exists():
        raise ValueError('The diagnostic workspace or evidence already exists.')
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    prompt = ROOT / CASE / 'prompt.txt'
    receipt = {'run_id': RUN_ID, 'registration_commit': args.registration_commit,
               'started_at': now(), 'prompt_sha256': sha256(prompt), 'accepted': False, 'completed': False}
    try:
        dsh(work, evidence, prompt.read_text(encoding='utf-8'), receipt)
    finally:
        probe = work / 'probe.txt'
        receipt['ended_at'] = now()
        receipt['probe_sha256'] = sha256(probe) if probe.is_file() else None
        write_json(evidence / 'operator.json', receipt)
    print(f"{RUN_ID}: accepted={receipt['accepted']} completed={receipt['completed']}")


if __name__ == '__main__':
    main()
