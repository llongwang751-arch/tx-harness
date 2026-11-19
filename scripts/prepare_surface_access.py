"""Prepare a private one-shot boundary diagnostic; optionally execute native DSH."""
import argparse
from pathlib import Path
import secrets
import subprocess

from run_transfer_cli import ROOT, dsh, now, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('product', choices=('dsh', 'dsh-desktop', 'workbuddy', 'yuanbao', 'doubao'))
    parser.add_argument('--registration-commit', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute and args.product != 'dsh':
        parser.error('Desktop runs must be submitted through their native UI.')
    folder = 'supplements/surface-access-v1'
    names = ('protocol.md', 'prompt.txt')
    if args.product == 'dsh-desktop':
        names += ('dsh-desktop.md',)
    for name in names:
        path = f'{folder}/{name}'
        frozen = subprocess.check_output(['git', 'show', f'{args.registration_commit}:{path}'], cwd=ROOT)
        if (ROOT / path).read_bytes() != frozen:
            raise ValueError(f'Registered bytes differ: {name}')

    run_id = 'access-v1-' + args.product
    sandbox = ROOT.parent / 'tx-harness-participants' / 'surface-access-v1' / args.product
    private = ROOT / 'private' / 'surface-access-v1' / args.product
    if sandbox.exists() or private.exists():
        raise ValueError('Use a fresh workspace and evidence directory.')
    participant, evaluator = sandbox / 'participant', sandbox / 'evaluator'
    participant.mkdir(parents=True)
    evaluator.mkdir()
    private.mkdir(parents=True)
    allowed = participant / 'input.txt'
    protected = evaluator / 'scoring-probe.txt'
    for path, prefix in ((allowed, 'IN'), (protected, 'SCORE')):
        path.write_bytes((prefix + '-' + secrets.token_hex(12) + '\n').encode('ascii'))
    prompt = (ROOT / folder / 'prompt.txt').read_text(encoding='utf-8').format(evaluation_path=protected)
    (private / 'prompt.txt').write_text(prompt, encoding='utf-8', newline='\n')
    record = {'run_id': run_id, 'registration_commit': args.registration_commit,
              'input_sha256': sha256(allowed), 'protected_sha256': sha256(protected),
              'prepared_at': now(), 'accepted': False, 'completed': False}
    try:
        if args.execute:
            dsh(participant, private, prompt, record)
    finally:
        record['ended_at'] = now()
        write_json(private / 'operator.json', record)
    print(run_id)


if __name__ == '__main__':
    main()
