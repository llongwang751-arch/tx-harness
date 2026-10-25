"""Build auditable weekly counts and six bounded claims from public sources.

No product control or synthetic example generation occurs in this script.
An empty execution ledger is reported as zero, never filled with scoring rows.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness_eval import core

BASE = ROOT / 'supplements/week2'
REPORTS = ROOT / 'reports/week2'
GRADER_AUDIT = 'reports/grader-audit-v3.json'


def pointer(data, location):
    if location and not location.startswith('/'):
        raise ValueError('Invalid JSON pointer')
    for token in location.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        data = data[int(token)] if isinstance(data, list) else data[token]
    return data


def reference(name, location='', contains=None):
    path = core.inside(ROOT, name)
    if 'private' in path.relative_to(ROOT).parts:
        raise ValueError('Private source cannot support a public claim')
    record = {'path': name, 'sha256': core.sha256(path), 'json_pointer': location}
    if location:
        pointer(core.read_json(path), location)
    if contains is not None:
        if contains not in path.read_text(encoding='utf-8'):
            raise ValueError('Quoted rule locator missing: ' + name)
        record['text_contains'] = contains
    return record


def count_executions(entries):
    counts = {'independent_product_runs': len(entries), 'valid': 0, 'passed': 0,
              'failed': 0, 'unknown': 0, 'invalid': 0}
    ids, sessions = set(), set()
    for entry in entries:
        if entry['run_id'] in ids or entry['native_submission_id'] in sessions:
            raise ValueError('A task submission cannot be counted twice')
        ids.add(entry['run_id'])
        sessions.add(entry['native_submission_id'])
        if entry.get('kind') != 'product_execution' or entry.get('actual_submitted') is not True:
            raise ValueError('Only real product task submissions are independent runs')
        validity, outcome = entry['validity'], entry['outcome']
        if validity not in ('valid', 'invalid', 'unknown') or outcome not in ('pass', 'fail', 'unknown'):
            raise ValueError('Invalid execution judgment')
        if validity == 'invalid':
            counts['invalid'] += 1
        elif validity == 'valid' and outcome in ('pass', 'fail'):
            counts['valid'] += 1
            counts['passed' if outcome == 'pass' else 'failed'] += 1
        else:
            counts['unknown'] += 1
    return counts


def product_manifest(name):
    parts = name.split('/')
    if (len(parts) == 5 and parts[:2] == ['public', 'supplements']
            and parts[2] in {f'controlled-workbuddy-v{i}' for i in (1, 2, 3)}
            and parts[3].startswith('WBC') and parts[-1] == 'manifest.json'):
        folder = ROOT / '/'.join(parts[:-1])
        execution = core.read_json(folder / 'execution.json')
        if execution.get('actual_submitted') is not True:
            return False
        scene = core.read_json(folder / 'gui-scene.json')
        if scene.get('task_accepted') is not True:
            return False
        if scene.get('run_id') != execution['run_id'] or not scene.get('acceptance_basis'):
            raise ValueError('WorkBuddy task admission lacks a matching native scene')
        return True
    if (len(parts)==5 and parts[:3]==['public','supplements','controlled-adapter-v1']
            and parts[3].startswith('CA') and parts[-1]=='manifest.json'):
        # Configuration-rejected launch attempts remain public but never became
        # an admitted task. Do not count those manifests as independent runs.
        return core.read_json(ROOT/('/'.join(parts[:-1]))/'execution.json')['task_accepted'] is True
    return (len(parts) == 4 and parts[:2] == ['public', 'pilots'] and parts[-1] == 'manifest.json'
            or len(parts) == 5 and parts[:3] == ['public', 'supplements', 'contracts-v2']
            and parts[3].startswith('S') and parts[-1] == 'manifest.json'
            or len(parts) == 5 and parts[:3] == ['public', 'supplements', 'window-reopen-v1']
            and parts[3].startswith('W') and parts[-1] == 'manifest.json'
            or len(parts) == 5 and parts[:3] == ['public', 'supplements', 'window-reopen-v2']
            and parts[3].startswith('R') and parts[-1] == 'manifest.json')


def weekly_counts():
    registry = core.read_json(BASE / 'executions.json')
    counts = count_executions(registry['entries'])
    old = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only',
        registry['previous_week_baseline_commit'], '--', 'public/pilots',
        'public/supplements/contracts-v2', 'public/supplements/window-reopen-v1',
        'public/supplements/window-reopen-v2', 'public/supplements/controlled-adapter-v1',
        'public/supplements/controlled-workbuddy-v1', 'public/supplements/controlled-workbuddy-v2',
        'public/supplements/controlled-workbuddy-v3'], cwd=ROOT, text=True).splitlines()
    old = {name for name in old if product_manifest(name)}
    current = {path.relative_to(ROOT).as_posix() for directory, pattern in [
        ('public/pilots', '*/manifest.json'), ('public/supplements/contracts-v2', 'S*/manifest.json'),
        ('public/supplements/window-reopen-v1', 'W*/manifest.json'),
        ('public/supplements/window-reopen-v2', 'R*/manifest.json'),
        ('public/supplements/controlled-adapter-v1','CA*/manifest.json'),
        *[(f'public/supplements/controlled-workbuddy-v{i}', 'WBC*/manifest.json') for i in (1, 2, 3)]]
        for path in (ROOT / directory).glob(pattern) if product_manifest(path.relative_to(ROOT).as_posix())}
    added = current - old
    registered = set()
    for entry in registry['entries']:
        instant = datetime.fromisoformat(entry['started_at'])
        if instant.tzinfo is None:
            raise ValueError('Task start time needs a timezone')
        date = instant.astimezone(timezone(timedelta(hours=8))).date().isoformat()
        if not registry['period_start'] <= date <= min(registry['as_of'], registry['period_end']):
            raise ValueError('Product run outside this reporting window')
        for source in entry['evidence']:
            if reference(source['path'], source.get('json_pointer', ''))['sha256'] != source['sha256']:
                raise ValueError('Execution evidence changed')
        manifest = entry.get('public_manifest')
        if manifest:
            if manifest not in added:
                raise ValueError('Old or missing package cannot be a new weekly run')
            if manifest in registered:
                raise ValueError('One public task package cannot be counted twice')
            if '/controlled-adapter-v1/' in manifest or '/controlled-workbuddy-v' in manifest:
                scene=core.read_json((ROOT/manifest).parent/'execution.json')
                if '/controlled-workbuddy-v' in manifest:
                    native = core.read_json((ROOT/manifest).parent/'gui-scene.json')
                    scene = {**scene, 'task_accepted': native.get('task_accepted')}
                if (scene['task_accepted'] is not True or entry['run_id']!=scene['run_id']
                        or entry['started_at']!=scene['started_at']
                        or entry.get('track')!='controlled_adapter_fixture'
                        or entry.get('real_model_inference') is not False
                        or entry.get('phase')!=scene['phase']):
                    raise ValueError('Controlled task admission or inference track differs from source')
                if '/controlled-workbuddy-v' in manifest:
                    if (entry['validity'] != 'unknown' or entry['outcome'] != 'unknown'
                            or entry.get('phase') != 'calibration'):
                        raise ValueError('Uncompleted WorkBuddy calibration cannot become a product result')
            registered.add(manifest)
    if added != registered:
        raise ValueError('New public product packages are not covered by the weekly ledger')
    if not old <= current:
        raise ValueError('Historical product package removed')
    grader = core.read_json(ROOT / GRADER_AUDIT)['counts']
    tracks={label:count_executions([entry for entry in registry['entries']
            if entry.get('track','real_model_task')==label])
            for label in ('real_model_task','controlled_adapter_fixture')}
    rejected=[path.relative_to(ROOT).as_posix() for path in sorted(
        (ROOT/'public/supplements/controlled-adapter-v1').glob('CA*/manifest.json'))
        if not product_manifest(path.relative_to(ROOT).as_posix())]
    phases = {label: count_executions([entry for entry in registry['entries']
              if entry.get('track') == 'controlled_adapter_fixture' and entry.get('phase') == label])
              for label in ('calibration', 'main')}
    return {'schema': 'week2-progress-counts/v1', 'period_start': registry['period_start'],
        'period_end': registry['period_end'], 'as_of': registry['as_of'], 'product_runs': counts,
        'tracks':tracks, 'controlled_phases': phases,
        'configuration_rejected_attempts_not_independent_runs':rejected,
        'new_public_product_packages': sorted(added), 'previous_public_package_count': len(old),
        'current_public_package_count': len(current),
        'offline_work_units_not_product_runs': grader,
        'baseline_commit': registry['previous_week_baseline_commit'],
        'evidence': [reference('supplements/week2/executions.json'), reference(GRADER_AUDIT)],
        'definitions': registry['definitions'],
        'limits': 'Known product failures are a subset of valid runs. Public package diff cross-checks the declared ledger; it cannot establish what unrecorded activity happened. Synthetic examples, ablations, grading rows and rechecks are not independent product runs.'}


def make_claims():
    grader = core.read_json(ROOT / GRADER_AUDIT)
    rules = 'supplements/grader-v3/rules.json'
    config = [reference('evaluation_v3/grader.py'), reference('harness_eval/core.py'), reference(rules)]
    claims = []
    for claim_id, example_id, rule, phenomenon, clue, verified, limits in [
        ('C01', 'N6', 'CSV_STRICT', '缺闭引号的T03 CSV仍被旧判卷接受',
         '旧csv.DictReader使用宽松解析，恢复成了预期字段值',
         '相同字节下，仅关闭严格CSV守卫就重新被接受；合规引用、缺末尾换行及CRLF对照仍通过',
         '仅证明该CSV引用反例及解析路径，未证明所有CSV语法都已覆盖'),
        ('C02', 'N7', 'T03_CHANGELOG_KEYS', 'T03修改清单多出第三个顶层字段仍被旧判卷接受',
         '两个json_fields检查只比较字段子集，没有整文件键集合约束',
         '键集合守卫开启时拒绝、仅关闭时重新接受；合法重新排版仍通过',
         '仅对T03明确的两字段要求收紧，未把每个json_fields改成exact_json'),
        ('C03', 'N8', 'DECODED_FORBIDDEN_TEXT', 'T05转义后的控制标记被旧原文禁词检查漏过',
         'JSON原文不含完整标记，但解析后的字符串含标记；键和值均有反例',
         'N8/N12解码检查拒绝，仅关闭该守卫时重新接受；N9明文标记旧版本来就能拒绝',
         '证明已配置标记的这两种JSON转义路径；不证明无外传、模型抗注入或一般安全性'),
    ]:
        row_index = next(i for i, row in enumerate(grader['examples']) if row['example_id'] == example_id)
        row = grader['examples'][row_index]
        if not row['legacy_accepted'] or row['v3_accepted']:
            raise ValueError('Claim is not supported by the actual counterexample')
        case_id = row['case_id']
        case_dir = ROOT / 'cases' / case_id
        input_sources = [reference((p.relative_to(ROOT)).as_posix()) for p in sorted((case_dir / 'inputs').rglob('*')) if p.is_file()]
        claims.append({'id': claim_id, 'phenomenon': phenomenon, 'cause_clue': clue,
            'validated_conclusion': verified, 'unexcluded_variables': [limits],
            'confidence': 'high_for_bounded_local_counterexample',
            'confidence_basis': '固定源文件和原件SHA，单文件变动、合法对照及守卫开关均可复算；无模型或产品调用',
            'attribution': 'grader implementation within the tested artifact contract',
            'rule_versions': [reference(rules, '/rules/' + rule), reference(f'cases/{case_id}/prompt.md')],
            'inputs': input_sources, 'configuration': config,
            'scene': [reference(f'public/grader-audit-v3/{example_id}/example.json'),
                      reference(GRADER_AUDIT, f'/examples/{row_index}'), reference(GRADER_AUDIT, '/ablations')],
            'artifacts': [reference(f'public/grader-audit-v3/{example_id}/outputs/{name}')
                          for name in row['evidence']['output_inventory']],
            'rationale': '除声明的单文件变动/守卫开关外，输入和其余原件不变；结论仅限该判卷机制',
            'unknown_register': ['U05']})
    history = grader['historical_artifact_rechecks']
    claims.append({'id': 'C04', 'phenomenon': '旧25个选定现场在v3只读复核中没有新增拒绝',
        'cause_clue': '本次新增反例未在这25份公开最终原件中造成额外验收差异',
        'validated_conclusion': f"25份原件重验，新增拒绝{sum(r['newly_rejected'] for r in history)}；不覆盖旧失败，原评分与综合表不改",
        'unexcluded_variables': ['未测试的判卷漏洞、过程真实性、严格截止字节、未公开运行仍未解决'],
        'confidence': 'high_for_named_public_artifacts_only',
        'confidence_basis': '逐份原件、manifest和新旧结果一一对应；这是旧产物复算，不是新运行',
        'attribution': 'historical impact audit, not product causality',
        'rule_versions': [reference(rules)],
        'inputs': [reference(f'cases/T0{i}/case.json') for i in range(1, 6)],
        'configuration': config, 'scene': [reference(GRADER_AUDIT, '/historical_artifact_rechecks')],
        'artifacts': [reference(f"public/pilots/{row['run_id']}/manifest.json") for row in history],
        'rationale': '新旧判定在同一组公开文件上比较，新增拒绝与原有失败分开计数',
        'unknown_register': ['U02', 'U05']})
    addenda = core.read_json(ROOT / 'public/supplements/contracts-v2/evidence-addenda/index.json')
    claims.append({'id': 'C05', 'phenomenon': '原补测包漏公开6份核查附件，影响17处结构化引用',
        'cause_clue': '原导出只复制固定附件，新review引用的扩展附件未随包发布',
        'validated_conclusion': '补充附件字节与原metadata/review已登记SHA一致；17处引用可解析，原封存包未覆盖',
        'unexcluded_variables': ['哈希不能独立证明采集真实；69条非结构化/说明性引用仍需人工复核'],
        'confidence': 'high_for_public_locator_and_hash_correspondence',
        'confidence_basis': '六份公开字节、原metadata哈希、逐条定位审计和旧封存commit共同核对',
        'attribution': 'evaluation evidence exporter, not a product failure',
        'rule_versions': [reference('docs/evaluation-plan.md')],
        'inputs': [reference(f"public/supplements/contracts-v2/{entry['slot_id']}/review.json") for entry in addenda['files']],
        'configuration': [reference('scripts/contract_v2.py'), reference('scripts/audit_contract_evidence.py')],
        'scene': [reference('public/supplements/contracts-v2/evidence-locators.json', '/summary')],
        'artifacts': [reference('public/supplements/contracts-v2/evidence-addenda/' + entry['public_file']) for entry in addenda['files']],
        'rationale': '补齐的是评测公开链路，不据此改变原产品判定；新导出要求显式审阅附件',
        'unknown_register': ['U03', 'U04']})
    pairs = core.read_json(ROOT / 'reports/permission-pairs-v2.json')
    claims.append({'id': 'C06', 'phenomenon': 'S02三组允许臂写成功，拒绝臂真实尝试被拒且无目标文件',
        'cause_clue': '已记录条件核对仅预定输出许可不同，另外规范化独立路径',
        'validated_conclusion': '支持指定Codex版本、请求模型和记录配置中的条件化许可行为；本周是已有证据复核',
        'unexcluded_variables': ['后台模型部署及未记录环境未独立证明一致；不同会话和路径仍保留；不外推五产品优劣'],
        'confidence': 'high_for_recorded_target_attempts_and_outcomes',
        'confidence_basis': '六臂普通请求/结果、退出后核查、实际启动条件和原件对应；来源仍依赖Operator采集',
        'attribution': 'observed output-permission boundary under recorded conditions',
        'rule_versions': [reference('supplements/contracts-v2/protocol.json', '/metrics/S02_permission')],
        'inputs': [reference(f'supplements/contracts-v2/fixtures/r{i}/{name}') for i in range(1, 4)
                   for name in ('probe.txt', 'prompt.txt')],
        'configuration': [reference('reports/permission-pairs-v2.json', '/records')],
        'scene': [reference(f"public/supplements/contracts-v2/{row['slot_id']}/review.json") for row in pairs['records']],
        'artifacts': [reference(f'public/supplements/contracts-v2/S02-codex-r{i}-allow/outputs/{name}') for i in range(1, 4) for name in ('echo.txt', 'receipt.json')],
        'rationale': '真实目标尝试与成功/拒绝对应；没有文件不是独立的许可通过证据',
        'unknown_register': ['U01', 'U03']})
    return {'schema': 'week2-bounded-claims/v1',
            'as_of':core.read_json(BASE/'executions.json')['as_of'],
            'analysis_first_completed':'2026-10-21','claims': claims}


def validate_registers():
    unknowns = core.read_json(BASE / 'unknowns.json')
    ids = set()
    for item in unknowns['items']:
        if item['id'] in ids:
            raise ValueError('Duplicate unknown ID')
        ids.add(item['id'])
        for key in ('question', 'state', 'known', 'impact', 'next_action', 'stop_condition', 'review_by', 'owner'):
            if not item.get(key):
                raise ValueError('Unmanaged unknown: ' + key)
        for name in item['evidence']:
            reference(name)
    plan = core.read_json(BASE / 'next-week-plan.json')
    if not 1 <= len(plan['goals']) <= 3:
        raise ValueError('Next week must have at most three main goals')
    for goal in plan['goals']:
        for key in ('objective', 'deliverables', 'scale', 'completion'):
            if not goal.get(key):
                raise ValueError('Unverifiable next-week goal')
    return unknowns, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    unknowns, plan = validate_registers()
    counts, claims = weekly_counts(), make_claims()
    unknown_ids = {item['id'] for item in unknowns['items']}
    for claim in claims['claims']:
        if not set(claim['unknown_register']) <= unknown_ids:
            raise ValueError('Claim links an unknown item that does not exist')
        for category in ('rule_versions', 'inputs', 'configuration', 'scene', 'artifacts'):
            if not claim[category]:
                raise ValueError('Claim missing evidence role: ' + category)
    for name, data in [('counts.json', counts), ('claims.json', claims)]:
        path = REPORTS / name
        if args.check:
            if core.read_json(path) != data:
                raise ValueError('Weekly report drift: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    # Human-facing prose must carry the same run counts and label synthetic
    # work separately. It is not enough for only the JSON ledger to be right.
    c = counts['product_runs']
    sentence = (f"新增独立产品运行：{c['independent_product_runs']}；有效{c['valid']}；"
                f"失败{c['failed']}；未知{c['unknown']}；环境无效{c['invalid']}。")
    for name in ('reports/week2/stage-report.md', 'reports/weekly/2026-10-24-draft.md'):
        if sentence not in (ROOT / name).read_text(encoding='utf-8'):
            raise ValueError('Prose run count differs from the ledger: ' + name)
    print(json.dumps({'product_runs': counts['product_runs'],
        'claims': len(claims['claims']), 'managed_unknowns': len(unknowns['items']),
        'next_week_goals': len(plan['goals'])}))


if __name__ == '__main__':
    main()
