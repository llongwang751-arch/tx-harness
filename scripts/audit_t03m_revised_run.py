"""Verify the revised T03-M run, access evidence and frozen score offline."""
from datetime import datetime
from hashlib import sha256 as hash_bytes
import json
import subprocess

from run_t03m_revised import CASE, REVIEW, ROOT, RUN_ID, check_registered, grade
from run_codex_pilot import DELIVERY_SUFFIX
from harness_eval.core import inventory, read_json, sha256


PUBLIC = ROOT / 'public/behavior-formal' / RUN_ID


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    require(inventory(PUBLIC, exclude=('manifest.json',)) == read_json(PUBLIC / 'manifest.json'),
            'Archived evidence differs from the manifest.')
    record = read_json(PUBLIC / 'observation.json')
    plan = check_registered(record['registration_commit'])
    require(record['run_id'] == plan['run_id'] and record['cli_binary_sha256'] == plan['cli_binary_sha256']
            and record['cli_version'] == plan['cli_version'], 'CLI or run differs from registration.')
    review = read_json(ROOT / REVIEW)
    history = read_json(ROOT / 'public/behavior-formal/t03m-assisted-review-2026-11-21.json')['historical_artifact_result']
    require(review['recomputed_artifact_score'] == history['score'] and all(
        entry['recomputed_passed'] == history['selected_checks'][name]['passed']
        for name, entry in review['checks'].items()), 'Independent recompute differs from the frozen replay.')

    access = read_json(PUBLIC / 'access.json')
    receipt = PUBLIC / 'access.stdout.jsonl'
    require(access['observation'] == read_json(receipt) and access['stdout_sha256'] == sha256(receipt),
            'Native access evidence differs from the original probe output.')
    require(record['tool_qualification_passed'] and access['exit_code'] == 0
            and access['executable_sha256'] == plan['cli_binary_sha256']
            and access['observation']['input_sha256'] == plan['participant_hashes'] == record['input_hashes_after']
            and access['observation']['protected_open'] == dict.fromkeys(('grader', 'rubric', 'oracle', 'reference'), 'denied:80070005'),
            'Native tool qualification or input integrity is invalid.')
    for asset in access['protected_files'].values():
        pinned = subprocess.check_output(['git', 'show', f"{plan['grader_commit']}:{asset['path']}"], cwd=ROOT)
        require(hash_bytes(pinned).hexdigest() == asset['host_sha256'], 'Probe targeted a different evaluator file.')
    frozen = (ROOT / 'supplements/t03m-prompt-review-v1/prompt.md').read_bytes()
    require((PUBLIC / 'submitted-prompt.md').read_bytes() == frozen + b'\n' + (DELIVERY_SUFFIX + '\n').encode('utf-8')
            and sha256(PUBLIC / 'submitted-prompt.md') == record['submitted_prompt_sha256'],
            'Submitted task differs from the frozen revision and delivery convention.')
    turn = record['native_turn']
    require(record['submitted'] and datetime.fromisoformat(access['ended_at']) < datetime.fromisoformat(turn['submitted_at']),
            'The required tool probe did not precede task submission.')
    events = read_json(PUBLIC / 'task-events.excerpts.json')
    require(len(events) == turn['native_event_count'] and any(row['type'] == 'turn.started' for row in events),
            'Native task start or full event coverage is unavailable.')
    terminal = any(row['type'] == 'turn.completed' for row in events)
    require(terminal == record['native_completed'], 'Reported task termination differs from the native events.')
    expected = set(read_json(CASE / 'case.json')['required_outputs'])
    actual = inventory(PUBLIC / 'outputs')
    require(actual == {item['path']: item['sha256'] for item in record['collection']['collected']}
            and set(actual) <= expected, 'Collected output bytes differ from the archived files.')
    completed = terminal and set(actual) == expected and turn['exit_code'] == 0 and not turn['timed_out']
    require(completed == (record['status'] == 'completed'), 'Task completion classification is inconsistent.')

    score = grade(PUBLIC / 'outputs')
    require(score == read_json(PUBLIC / 'score.json'), 'Frozen grader result differs from the archived score.')
    print(json.dumps({'run_id': RUN_ID, 'status': record['status'],
                      'artifact_score': score['legacy_artifact_result']['objective_score'],
                      'accepted': score['accepted']}))


if __name__ == '__main__':
    main()
