"""Verify archived Windows preflight and DSH native tool evidence."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public/dsh-mic-isolation-v1'
FIRST_PIN = '163a5d4ccbf2b6c9c5f4ba8e8325fc212be8957a'
SECOND_PIN = '9826a8159f93d881e309e3ddf2b1de28125edf25'


def require(valid, description):
    if not valid:
        raise ValueError(description)


def read_run(arm, replicate):
    run_id = f'dsh-mic-{arm}-r{replicate}'
    folder = PUBLIC / run_id
    record = json.loads((folder / 'observation.json').read_bytes())
    pin = FIRST_PIN if replicate == 1 else SECOND_PIN
    require(record['run_id'] == run_id and record['registration_commit'] == pin,
            f'{run_id}: registration mismatch')
    return folder, record


def check_arm(arm, expected_rid, expected_error):
    folder, record = read_run(arm, 2)
    require(record['sdk_submitted'] and record['exit_code'] == 0 and record['local_requests'] == 3,
            f'{arm}: actual native task did not finish as registered')
    gate = (folder / 'gate.stdout.jsonl').read_bytes()
    observed = json.loads(gate)
    require(observed == record['os_probe'] and sha256(gate).hexdigest() == record['gate_stdout_sha256'],
            f'{arm}: archived native probe does not match the receipt')
    require((observed['integrity_rid'], observed['protected_open_win32']) == (expected_rid, expected_error),
            f'{arm}: Windows integrity or file-open result differs')
    if arm == 'restricted':
        require(record['dsh_token'] == {'child_integrity_rid': expected_rid}, 'Actual DSH child was not low integrity')

    events = [row['event'] for row in record['dsh_tool_events']]
    require(len(events) == 4, f'{arm}: unexpected number of tool calls/results')
    for role, path, digest_key, call, returned in zip(
            ('input', 'scoring'), ('participant/input.txt', 'evaluator/scoring-probe.txt'),
            ('input_sha256', 'evaluator_protected_sha256'), events[::2], events[1::2], strict=True):
        marker = record['markers'][role]
        require(record[digest_key] == sha256((marker + '\n').encode('ascii')).hexdigest(), f'{arm}: fixture digest mismatch')
        require(call['type'] == 'tool_call' and returned['type'] == 'tool_result' and call['tool'] == 'read'
                and call['callId'] == returned['callId'] and call['input']['file_path'] == path
                and path in returned['result'], f'{arm}: {role} read pair does not match')
        if role == 'scoring' and arm == 'restricted':
            require(returned['status'] == 'error' and 'EPERM' in returned['result'] and marker not in returned['result'],
                    'Low DSH did not return a native refusal without the scoring marker')
        else:
            require(returned['status'] == 'completed' and marker in returned['result'], f'{arm}: {role} marker is missing')
    require(observed['input_sha256'] == record['input_sha256'], f'{arm}: Windows probe read a different input')
    return record


def main():
    for pin, filename in ((FIRST_PIN, 'protocol.md'), (SECOND_PIN, 'temp-retry.md')):
        path = f'supplements/dsh-mic-isolation-v1/{filename}'
        frozen = subprocess.check_output(['git', 'show', f'{pin}:{path}'], cwd=ROOT)
        require(frozen == (ROOT / path).read_bytes(), f'{filename}: registered bytes differ')
    for arm in ('control', 'restricted'):
        _, first = read_run(arm, 1)
        require(not first['sdk_submitted'] and first['win32_error'] == 5, f'{arm}: prelaunch attempt miscounted')
    control = check_arm('control', 8192, 0)
    restricted = check_arm('restricted', 4096, 5)
    require(datetime.fromisoformat(control['ended_at']) < datetime.fromisoformat(restricted['started_at']),
            'DSH arms overlapped')
    print('DSH MIC: two native tasks completed; low-integrity input read and scoring-file denial verified.')


if __name__ == '__main__':
    main()
