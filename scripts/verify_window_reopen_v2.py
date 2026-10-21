"""Recompute the published, preregistered native-UI/local-file pair.

Hashes and selected AX/action records establish internal consistency, not an
independent authentication of the operator's observations or cloud storage.
"""
from __future__ import annotations

from datetime import timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.window_reopen import judge
from scripts.window_reopen_v2 import close_verdict, direct_verdict, instant, time_verdict

BASE = ROOT / 'public/supplements/window-reopen-v2'
PROTOCOL = 'supplements/window-reopen-v2/protocol.json'
REGISTRATION = '51cd34f436f22f66f22dddd8e2d14a94535a362c'
PROBE = 'supplements/window-reopen-v2/fixtures/probe.txt'
PROMPT = 'supplements/window-reopen-v2/fixtures/prompt.txt'
RETRIEVALS = {f'{phase}/{name}' for phase in ('retrieval-before', 'retrieval-after')
              for name in ('probe.txt', 'stage-a.txt')}
ACQUISITIONS = RETRIEVALS | {f'stage-b/{name}' for name in ('stage-a.txt', 'stage-b.txt', 'receipt.json')}
HEX = re.compile(r'[0-9a-f]{64}')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)


def jsonl(path):
    return [json.loads(line, object_pairs_hook=unique_object)
            for line in path.read_text(encoding='utf-8').splitlines()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(directory, relative):
    """Evidence references are package-relative POSIX paths, never native paths."""
    name = PurePosixPath(relative)
    require(relative and '\\' not in relative and ':' not in relative and
            not name.is_absolute() and '..' not in name.parts, f'Unsafe evidence path: {relative}')
    path = directory / name
    require(path.resolve().is_relative_to(directory.resolve()) and path.is_file(),
            f'Evidence missing or outside package: {relative}')
    return path


def check_manifest(directory):
    manifest = read(directory / 'manifest.json')
    require(manifest['schema'] == 'window-reopen-public-package/v2', 'Manifest schema')
    require(manifest['run_id'] == directory.name, 'Manifest run identity')
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*')
              if p.is_file() and p != directory / 'manifest.json'}
    require(actual == set(manifest['files']), 'Package file inventory differs')
    for name, spec in manifest['files'].items():
        path = local(directory, name)
        require(not path.is_symlink(), f'Symlink in package: {name}')
        require(path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256'],
                f'Package hash/size differs: {name}')


def registered_protocol():
    """Bind both current bytes and historical git blobs before reading outcomes."""
    def blob(name):
        return subprocess.check_output(['git', 'show', f'{REGISTRATION}:{name}'], cwd=ROOT)
    require(blob(PROTOCOL) == (ROOT / PROTOCOL).read_bytes(), 'Registered protocol changed')
    protocol = read(ROOT / PROTOCOL)
    require(len(protocol['files']) == 8, 'Expected eight registered supporting files')
    for name, spec in protocol['files'].items():
        path = ROOT / name
        require(path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256'],
                f'Registered source hash/size differs: {name}')
        require(blob(name) == path.read_bytes(), f'Registered source blob differs: {name}')
    at = subprocess.check_output(['git', 'show', '-s', '--format=%cI', REGISTRATION],
                                 cwd=ROOT, text=True).strip()
    return protocol, instant(at)


def scenes(directory):
    mapping = read(directory / 'scene-index.json')
    require(len(mapping) == len(set(mapping.values())), 'Scene aliases are not one-to-one')
    actual = {p.relative_to(directory).as_posix() for p in (directory / 'scenes').glob('*.json')}
    require(actual == set(mapping.values()), 'AX scene index is not exhaustive')
    result = {}
    for source, public in mapping.items():
        data = read(local(directory, public))
        require(source.startswith('captures/') and source.endswith('.ax.txt'), 'Original scene path')
        require(data['schema'] == 'reviewed-native-ax-excerpt/v1' and
                data['source_capture'] == source and HEX.fullmatch(data['source_sha256']),
                'AX excerpt source metadata')
        rows = data['lines']
        nums = [row['line'] for row in rows]
        require(nums and all(type(n) is int and n > 0 for n in nums) and
                nums == sorted(set(nums)), 'AX source line numbers must increase without duplication')
        require(all(isinstance(row['text'], str) for row in rows) and data['review'], 'AX excerpt review')
        result[source] = (instant(data['captured_at']), '\n'.join(row['text'] for row in rows))
    return result


def clock_consistent(start, at, elapsed_ms, limit):
    observed = instant(at)
    require(type(elapsed_ms) in (int, float) and 0 <= elapsed_ms <= limit and
            abs((observed-start).total_seconds()*1000-elapsed_ms) < 1000,
            'Wall clock and monotonic elapsed/budget disagree')
    return observed


def check_custody(directory, protocol, start, seal, scene_map):
    budget = protocol['run_budget_seconds']*1000
    require(seal['budget_seconds'] == protocol['run_budget_seconds'] and seal['within_budget'] is True,
            'Seal budget metadata')
    end = clock_consistent(start, seal['at'], seal['elapsed_ms'], budget)
    rows = jsonl(directory / 'collection.jsonl')
    require(rows == seal['inventory'], 'Seal does not bind exact acquisition journal')
    names = []
    indexed = {}
    previous_time, previous_elapsed = start, 0
    for row in rows:
        require(row['collected'].count('/collected/') == 1, 'Ambiguous custody path')
        name = row['collected'].split('/collected/', 1)[1]
        names.append(name)
        require(row['collected'].startswith(f'D:/tx-harness/private/window-reopen-v2/{directory.name}/collected/'),
                'Custody run identity')
        acquired = clock_consistent(start, row['at'], row['elapsed_ms'], seal['elapsed_ms'])
        require(previous_time <= acquired <= end and previous_elapsed <= row['elapsed_ms'],
                'Acquisition journal is not chronological')
        previous_time, previous_elapsed = acquired, row['elapsed_ms']
        path = local(directory, 'collected/'+name)
        require(path.stat().st_size == row['bytes'] and digest(path) == row['sha256'],
                'Acquired bytes differ from custody receipt')
        require(row['scene'] in scene_map and scene_map[row['scene']][0] <= acquired,
                'Custody lacks prior native source scene')
        if name.startswith('stage-b/'):
            filename = name.split('/')[1]
            require(row['source'] == protocol['workspace_paths'][directory.name]+'/'+filename,
                    'Final artifact source is not the registered workspace')
            text = scene_map[row['scene']][1]
            require(all(token in text for token in (directory.name, 'harness-window-reopen-v2',
                                                    '本地磁盘 (D:)', filename)),
                    'Native directory excerpt does not locate final artifact')
        else:
            require(row['source'] == f'D:/harness-window-reopen-v2/acquisitions/{directory.name}/{name}',
                    'Native acquisition destination differs')
        indexed[name] = row
    actual = {p.relative_to(directory / 'collected').as_posix()
              for p in (directory / 'collected').rglob('*') if p.is_file()}
    require(len(names) == len(set(names)) == 7 and set(names) == actual == ACQUISITIONS,
            'Need exactly seven unique original acquisitions')
    return end, indexed


def full_message(text, prompt, title, start):
    require(title and title in text, 'Task title missing from original-message scene')
    local_time = start.astimezone(timezone(timedelta(hours=8))).strftime('%H:%M')
    require('文本 '+local_time in text, 'Original message creation time missing')
    cursor = 0
    for line in prompt.splitlines():
        if line:
            found = text.find(line, cursor)
            require(found >= 0, 'Original frozen prompt line missing or reordered')
            cursor = found + len(line)


def is_workbuddy_window(window):
    return (isinstance(window.get('app'), str) and window['app'].replace('\\', '/').lower().endswith('/workbuddy.exe')
            and type(window.get('id')) is int and window.get('title') == 'WorkBuddy')


def check_direct(directory, probe, prompt, start, checkpoint, primary, receipts, custody, scene_map):
    require(direct_verdict(probe, directory / 'collected', receipts), 'Frozen direct-retrieval check failed')
    checkpoint_at, primary_at = instant(checkpoint['at']), instant(primary['at'])
    for row in receipts:
        name = row['relative_path']
        acquisition = custody[name]
        require(all(row[key] == acquisition[key] for key in ('at', 'elapsed_ms', 'bytes', 'sha256')) and
                row['destination_scene'] == acquisition['scene'], 'UI receipt and custody journal disagree')
        require(row['source_scene'] in scene_map and row['destination_scene'] in scene_map,
                'UI receipt has unresolved scene reference')
        source_at, source = scene_map[row['source_scene']]
        destination_at, destination = scene_map[row['destination_scene']]
        acquired_at = instant(row['at'])
        require(start <= source_at <= destination_at <= acquired_at, 'UI source/save/acquisition order')
        if name.startswith('retrieval-before/'):
            require(acquired_at <= checkpoint_at, 'Baseline file obtained after checkpoint')
        else:
            require(checkpoint_at <= source_at <= acquired_at <= primary_at,
                    'After retrieval outside checkpoint/primary interval')
        filename = name.split('/')[1]
        require('菜单项 分享 '+filename in source, 'Wrong selected native file in source scene')
        native_card = r'\b组 probe\.txt' if filename == 'probe.txt' else r'\b按钮 stage-a\.txt'
        require(re.search(native_card, source), 'Original native attachment/delivery card absent')
        require('对话框 另存为' in destination and
                acquisition['source'].replace('/', '\\') in destination,
                'Save As dialog does not name acquired destination')
        if name == 'retrieval-after/probe.txt':
            full_message(source, prompt, primary['task_title'], start)


def check_actions(directory, start, end, submission, checkpoint, primary, continuation, protocol, receipts, scene_map):
    rows = jsonl(directory / 'actions.jsonl')
    times = [instant(row['at']) for row in rows]
    require(times == sorted(times), 'Action journal not chronological')
    labels = [row['label'] for row in rows]
    require(len(labels) == len(set(labels)), 'Duplicate action labels')
    initial = [r for r in rows if r['label'] in ('initial-submit', 'initial-task-submit')]
    continued = [r for r in rows if r['label'] == 'fixed-continuation-submit']
    require(len(initial) == len(continued) == 1, 'Expected exactly one initial and one continuation submission')
    for row, before, after in ((initial[0], submission['before_at'], submission['after_at']),
                               (continued[0], continuation['before_at'], continuation['after_at'])):
        require(instant(before) <= instant(row['at']) <= instant(after) and
                row['method'] == 'click' and row['result'] == 'returned', 'Submission action receipt mismatch')
    cp, main = instant(checkpoint['at']), instant(primary['at'])
    for row in rows:
        if cp <= instant(row['at']) <= main:
            require(row['method'] in ('click', 'scroll') or
                    (row['method'] == 'pressKey' and row['args'] == ['Return'] and
                     row['label'].startswith('native-save-')) or
                    (directory.name == 'R01-reopen' and row['label'] == 'planned-normal-close' and
                     row['method'] == 'pressKey' and row['args'] == ['alt+F4']),
                    'Unexpected message/input operation during primary')
    pasted = [r for r in rows if r['method'] == 'paste' and r['args'] == [protocol['continuation_message']]]
    require(len(pasted) == 1 and main <= instant(pasted[0]['at']) <= instant(continuation['before_at']),
            'Fixed continuation text/action order')
    for relative in RETRIEVALS:
        phase, filename = relative.split('/')
        saves = [r for r in rows if r['label'] == f'native-save-{phase}-{filename}']
        require(len(saves) == 1 and saves[0]['method'] == 'pressKey' and saves[0]['args'] == ['Return']
                and saves[0]['result'] == 'returned', 'Missing native Save As confirmation')
        receipt = next(row for row in receipts if row['relative_path'] == relative)
        require(scene_map[receipt['destination_scene']][0] <= instant(saves[0]['at']) <= instant(receipt['at']),
                'Save confirmation outside destination/acquisition interval')
    return rows


def verify_run(directory, protocol, registered_at):
    check_manifest(directory)
    run = directory.name
    execution = read(directory / 'execution.json')
    require(execution['registration_commit'] == REGISTRATION and execution['run_id'] == run and
            execution['actual_submitted'] is True, 'Execution submission identity')
    require(execution['input_sha256'] == protocol['files'][PROBE]['sha256'] and
            execution['prompt_sha256'] == protocol['files'][PROMPT]['sha256'], 'Frozen input/prompt identity')
    configuration = execution['configuration']
    for key in ('product', 'version_label', 'mode', 'model_label', 'permission_label'):
        require(configuration[key] == protocol[key], f'Visible configuration changed: {key}')
    require(configuration['workspace'] == protocol['workspace_paths'][run] and
            configuration['attachment_source'] == protocol['attachment_source_path'] and
            configuration['source_file_remains_present'] is True and configuration['skill'],
            'Workspace/attachment/Skill conditions')
    for name in execution['evidence']:
        local(directory, name)
    scene_map = scenes(directory)
    submission = read(directory / 'submission.json')
    start = instant(execution['started_at'])
    require(start >= registered_at and start == instant(submission['before_at']) and
            submission['registration_commit'] == REGISTRATION[:7] and submission['run_id'] == run and
            submission['workspace'] == configuration['workspace'], 'Submission/pre-registration timing or identity')
    require(submission['after_monotonic_ms'] >= submission['before_monotonic_ms'], 'Submission monotonic order')
    clock_consistent(start, submission['after_at'],
                     submission['after_monotonic_ms']-submission['before_monotonic_ms'], 1200000)
    seal = read(directory / 'seal.json')
    end, custody = check_custody(directory, protocol, start, seal, scene_map)
    require(end == instant(execution['ended_at']), 'Execution end differs from seal')
    checkpoint = read(directory / 'checkpoint.json')
    primary = read(directory / 'primary.json')
    continuation = read(directory / 'continuation.json')
    cp_at = clock_consistent(start, checkpoint['at'],
                             checkpoint['monotonic_ms']-submission['before_monotonic_ms'], seal['elapsed_ms'])
    primary_at = clock_consistent(start, primary['at'], primary['elapsed_ms'], seal['elapsed_ms'])
    require(start < cp_at < primary_at < instant(continuation['before_at']) <=
            instant(continuation['after_at']) < end and time_verdict(checkpoint, continuation),
            'Checkpoint/primary/continuation timing failed')
    require(checkpoint['run_id'] == run and checkpoint['task_title'] == primary['task_title'] and
            primary['message_accessible'] is True and primary['original_attachment_card_accessible'] is True
            and primary['native_retrieval_count'] == 4 and
            primary['model_messages_between_checkpoint_and_primary'] == 0, 'Primary record conditions')
    receipts = read(directory / 'ui-retrieval.json')
    probe, prompt = (ROOT / PROBE).read_bytes(), (ROOT / PROMPT).read_text(encoding='utf-8')
    check_direct(directory, probe, prompt, start, checkpoint, primary, receipts, custody, scene_map)
    actions = check_actions(directory, start, end, submission, checkpoint, primary, continuation, protocol,
                            receipts, scene_map)
    # The AX does not mark the selected radio state reliably: mode has screenshot/operator support.
    initial_scenes = [text for at, text in scene_map.values() if at <= start]
    config_text = '\n'.join(initial_scenes)
    require(all(token in config_text for token in (protocol['model_label'], protocol['permission_label'],
                                                   '单选按钮 (selectable) 办公', run, 'probe.txt')),
            'Pre-submission visible labels/input scene missing')
    if run == 'R01-reopen':
        proof = read(directory / 'close-proof.json')
        require(close_verdict(proof), 'Frozen close-intervention check failed')
        require(all(is_workbuddy_window(w) for w in proof['before_windows']) and
                all(is_workbuddy_window(w) for row in proof['observations'] for w in row['windows']),
                'Close inventories do not identify WorkBuddy windows')
        require(cp_at <= instant(proof['close_started_at']) <= instant(proof['restored_at']) <= primary_at,
                'Close intervention outside checkpoint/primary interval')
        close = [r for r in actions if r['label'] == 'planned-normal-close']
        require(len(close) == 1 and close[0]['method'] == 'pressKey' and close[0]['args'] == ['alt+F4']
                and instant(proof['close_started_at']) <= instant(close[0]['at']) <=
                instant(proof['observations'][0]['at']), 'Normal close action and inventory order')
        require(proof['identity_scene'] in scene_map, 'Restored task scene absent')
        identity_at, identity = scene_map[proof['identity_scene']]
        require(instant(proof['launch_at']) <= identity_at <= instant(proof['restored_at']), 'Restore scene timing')
        full_message(identity, prompt, primary['task_title'], start)
        require(proof['before_windows'][0]['id'] == submission['window_id'], 'Closed window identity')
        status = 'pass'
    else:
        proof = read(directory / 'control-proof.json')
        require(proof['claim'] == 'window_kept_open' and cp_at <= instant(proof['at']) <= primary_at and
                any(is_workbuddy_window(w) and w['id'] == submission['window_id'] for w in proof['windows']),
                'Open-control window evidence')
        require(not any(r['method'] == 'pressKey' and any('f4' in str(a).lower() for a in r['args'])
                        for r in actions if start <= instant(r['at']) <= end), 'Control contains close action')
        status = 'not_applicable'
    actual_judgment = judge(probe, directory / 'outputs')
    require(actual_judgment == read(directory / 'judgment.json'), 'Frozen byte/receipt judgment differs')
    for name in ('stage-a.txt', 'stage-b.txt', 'receipt.json'):
        require((directory / 'outputs' / name).read_bytes() ==
                (directory / 'collected/stage-b' / name).read_bytes(), 'Judged files differ from sealed originals')
        require(instant(custody['stage-b/'+name]['at']) >= instant(continuation['after_at']),
                'Final original acquired before Stage B continuation')
    artifact = 'pass' if actual_judgment['joint_delivery_pass'] else 'fail'
    require(execution['validity'] == 'valid' and execution['primary_outcome'] == 'pass' and
            execution['artifact_outcome'] == execution['outcome'] == artifact, 'Execution result disagrees')
    review = read(directory / 'review.json')
    require(review['rule_version'] == 'window-reopen/v2' and
            review['configuration'] == 'execution.json#/configuration' and review['artifacts'] == 'judgment.json',
            'Review rule/configuration/artifact references')
    # Review links target the package's published repository location, even when
    # a package copy is being checked in an isolated mutation-test directory.
    canonical = BASE / run
    require((canonical / review['rules']).resolve() == ROOT / PROTOCOL and
            {(canonical / p).resolve() for p in review['inputs']} == {ROOT / PROBE, ROOT / PROMPT},
            'Review rules/inputs differ from registered sources')
    for metric in review['metrics'].values():
        require(metric['status'] in ('pass', 'fail', 'unknown', 'not_applicable') and
                metric['reason'] and metric['confidence'] and metric['evidence'], 'Review metric lacks rationale')
        for name in metric['evidence']:
            local(directory, name)
    metrics = review['metrics']
    require(metrics['window_intervention']['status'] == status and
            metrics['stage_b_joint_delivery']['status'] == artifact and
            metrics['attachment_cloud_storage']['status'] == 'unknown', 'Review status overstates evidence')
    require(all(metrics[k]['status'] == 'pass' for k in ('original_message_accessible',
            'original_attachment_direct_retrieval', 'existing_stage_a_direct_retrieval',
            'operator_model_messages_during_primary')), 'Primary review differs')
    require(all(review[k] for k in ('phenomenon', 'cause_clue', 'validated_conclusion', 'unexcluded_variables')),
            'Review lacks attribution boundaries')
    known = {item['id'] for item in read(ROOT / 'supplements/week2/unknowns.json')['items']}
    require(set(review['unknown_register']) <= known, 'Unregistered unknown reference')
    return {'run_id': run, 'validity': execution['validity'], 'outcome': execution['outcome'],
            'primary_outcome': execution['primary_outcome'], 'joint_delivery_pass': actual_judgment['joint_delivery_pass'],
            'sealed_elapsed_ms': seal['elapsed_ms'], 'started_at': execution['started_at'], 'ended_at': execution['ended_at']}


def verify():
    protocol, registered_at = registered_protocol()
    index = read(BASE / 'index.json')
    require(index['schema'] == 'window-reopen-public-index/v2' and
            index['registration_commit'] == REGISTRATION and index['runs'] == protocol['order'] and
            len(index['runs']) == protocol['max_initial_submissions'] == 2, 'Public pair registration/count')
    actual = {p.name for p in BASE.iterdir() if p.is_dir()}
    require(actual == set(index['runs']), 'Unindexed run directories')
    results = [verify_run(BASE / run, protocol, registered_at) for run in index['runs']]
    require(instant(results[0]['ended_at']) < instant(results[1]['started_at']), 'Fixed order or single-active-run condition')
    counts = {'new_independent_product_runs': len(results),
              'known_valid_runs': sum(r['validity'] == 'valid' for r in results),
              'known_passed_runs': sum(r['validity'] == 'valid' and r['outcome'] == 'pass' for r in results),
              'failed_runs': sum(r['validity'] == 'valid' and r['outcome'] == 'fail' for r in results),
              'unknown_runs': sum(r['validity'] == 'unknown' or r['outcome'] == 'unknown' for r in results)}
    require(all(index[k] == v for k, v in counts.items()), 'Public pair count mismatch')
    require(index['pair_scope'], 'Pair scope missing')
    result = {'verified_runs': results, **counts,
              'limits': 'Recorded hash/contract/timing/UI-excerpt consistency only; operator observations are not independently authenticated. Local source remained present; no cloud-storage or hidden-model/Skill proof.'}
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    verify()
