"""Reconcile five-product attribution scope against pinned public evidence.

This is a retrospective source audit. It neither runs products nor proves the
authenticity of operator observations. It never awards a pure Harness score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_week2 import pointer

ASSESSMENT = 'supplements/attribution-audit-v1/assessment.json'
BASELINE = 'b8cd4f95e7036e1fd35102fc5e96e430d44e5105'
PRODUCTS = ('codex', 'workbuddy', 'dsh', 'yuanbao', 'doubao')
METRICS = ('input_read', 'missing_feedback', 'write_fidelity')
COVERAGE = 'public/supplements/contracts-v2/coverage.json'


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_path(name):
    parts = PurePosixPath(name)
    require(name and '\\' not in name and ':' not in name and not parts.is_absolute()
            and '..' not in parts.parts and not {'private', '.git'} & set(parts.parts),
            'Source must be a public repository path')
    path = ROOT / parts
    require(path.resolve().is_relative_to(ROOT.resolve()) and path.is_file(), 'Public source missing')
    return path


def validate_assessment(spec):
    require(spec['schema'] == 'attribution-source-review/v1' and
            spec['source_baseline_commit'] == BASELINE and
            spec['kind'] == 'retrospective_public_source_audit', 'Review version/baseline/scope changed')
    require(type(spec['new_product_runs']) is int and spec['new_product_runs'] == 0,
            'A source review is not a product run')
    require(spec['pure_harness_ranking_supported'] is False, 'No matched five-product causal ranking')
    require([r['product_id'] for r in spec['products']] == list(PRODUCTS), 'Need five distinct products')
    for row in spec['products']:
        require(row['model_control'] == 'requested_or_visible_label_only',
                'A requested model or label is not backend attestation')
        require(row['skill_control'] in ('partial', 'unknown') and row['all_skills_disabled_attested'] is False,
                'Partial/unknown Skill control cannot become fully disabled')
        require(row['independent_harness_causal_claim'] is False, 'Independent Harness attribution unsupported')
        for key in ('model', 'skill', 'phenomenon', 'cause_clue', 'validated_conclusion',
                    'confidence', 'confidence_basis', 'next_action', 'stop_condition'):
            require(isinstance(row.get(key), str) and row[key].strip(), 'Missing reviewed claim field: '+key)
        required = {(f'public/supplements/contracts-v2/S01-{row["product_id"]}-r{r}/{name}', location)
                    for r in range(1, 4) for name, location in
                    (('review.json', '/visible_conditions'), ('metadata.json', '/backend_model_attested'))}
        refs = [(r['path'], r['json_pointer']) for r in row['evidence']]
        require(len(refs) == len(set(refs)) and required <= set(refs), 'All three configurations must be retained')
    decision = spec['new_experiment_decision']
    require(decision['execute_now'] is False and decision['reason'] and decision['reopen_gate']
            and decision['scope_if_unmet'], 'Need a bounded stop/reopen decision')


def verify_sources(spec):
    refs = spec['aggregate_sources'] + [r for row in spec['products'] for r in row['evidence']]
    cached = {}
    values = {}
    for ref in refs:
        name, location = ref['path'], ref['json_pointer']
        path = public_path(name)
        if name not in cached:
            current = path.read_bytes()
            original = subprocess.check_output(['git', 'show', f'{BASELINE}:{name}'], cwd=ROOT)
            require(current == original, 'Historical source changed: '+name)
            cached[name] = (hashlib.sha256(current).hexdigest(), json.loads(current))
        sha, value = cached[name]
        require(re.fullmatch(r'[0-9a-f]{64}', ref['sha256']) and sha == ref['sha256'],
                'Source reference hash differs: '+name)
        actual = pointer(value, location)
        values[(name, location)] = actual
        if location == '/backend_model_attested':
            require(actual is False, 'Backend provenance changed; requires a new review version')
    require(any(r['path'] == COVERAGE and r['json_pointer'] == '' for r in spec['aggregate_sources']),
            'Coverage source missing')
    # These particular DSH facts prevent blanket no-Skill or blind-review claims.
    for run, field in (('r2', 'actual_diagnostic_skill_call_visible'), ('r3', 'actual_skill_call_visible')):
        key = (f'public/supplements/contracts-v2/S01-dsh-{run}/review.json', '/visible_conditions/skills/'+field)
        require(values.get(key) is True, 'Actual DSH Skill calls must remain in the review')
    key = ('public/supplements/contracts-v2/S01-dsh-r2/review.json', '/limitations/7')
    require(isinstance(values.get(key), str) and values[key], 'DSH observer exposure limitation missing')
    return cached[COVERAGE][1]


def product_metrics(coverage, product):
    rows = [r for r in coverage['rows'] if r['card'] == 'S01' and r['product_id'] == product]
    expected = {f'S01-{product}-r{r}' for r in range(1, 4)}
    require(len(rows) == 3 and {r['slot_id'] for r in rows} == expected
            and all(r['public_state'] == 'sealed' for r in rows), 'Do not select only successful/eligible attempts')
    result = []
    for metric in METRICS:
        observations = [r['observations'][metric] for r in rows]
        require(all((type(o['eligible']) is bool or o['eligible'] is None) and o['verdict'] in
                    ('pass', 'fail', 'unknown', 'upstream_deviation') and
                    (o['eligible'] is not None or o['verdict']=='unknown')
                    for o in observations), 'Observation status')
        counted = {
            'public_started':len(rows), 'eligible':sum(o['eligible'] is True for o in observations),
            'passed':sum(o['eligible'] is True and o['verdict']=='pass' for o in observations),
            'failed':sum(o['eligible'] is True and o['verdict']=='fail' for o in observations),
            'unknown_verdict':sum(o['verdict']=='unknown' for o in observations),
            'upstream_deviation':sum(o['verdict']=='upstream_deviation' for o in observations),
            'ineligible_or_evidence_missing':sum(o['eligible'] is not True for o in observations)}
        located = [(i,r) for i,r in enumerate(coverage['metric_denominators'])
                   if r['card']=='S01' and r['product_id']==product and r['metric']==metric]
        require(len(located)==1, 'Missing or duplicate metric denominator')
        i, original = located[0]
        require(all(original[k]==v for k,v in counted.items()), 'Denominator disagrees with all three attempts')
        result.append({'metric':metric, **counted,
            'eligibility_not_attested':sum(o['eligible'] is None for o in observations),
            'applicability_not_attested':original['applicability_not_attested'],
            'environment_validity_not_attested':original['environment_validity_not_attested'],
            'source_pointer':f'/metric_denominators/{i}',
            'scope':'Conditional observed boundary; eligibility is not randomized and may depend on Model/Skill/Harness. Not an overall causal success rate.'})
    e2 = [r for r in coverage['e2_delivery_denominators'] if r['card']=='S01' and r['product_id']==product]
    require(len(e2)==2 and {r['artifact'] for r in e2}=={'echo','receipt'}, 'E2 delivery denominator')
    for r in e2:
        require(r['planned']==r['public_sealed']==3 and
                r['original_obtained']+r['original_not_obtained']==3,
                'Keep obtained and absent original denominator')
    return result, e2


def build(spec):
    validate_assessment(spec)
    coverage = verify_sources(spec)
    products = []
    for entry in spec['products']:
        metrics, e2 = product_metrics(coverage, entry['product_id'])
        products.append({**entry, 's01_metrics':metrics, 's01_e2_delivery':e2,
                         'pure_harness_causal_score':None})
    return {'schema':'attribution-boundary-audit/v1','as_of':spec['reviewed_at'],
        'source_baseline_commit':BASELINE, 'assessment':{'path':ASSESSMENT,'sha256':digest(ROOT/ASSESSMENT)},
        'new_independent_product_runs':0,'source_s01_runs_reviewed':15,
        'pure_harness_ranking_supported':False,'products':products,
        'new_experiment_decision':spec['new_experiment_decision'],
        'limits':'Checks source versions, locators, all-attempt denominators and declared scope. Narrative attribution remains a reviewed interpretation; hashes and checks do not authenticate the original operator or prove hidden controls.'}


def render(data):
    lines = ['# 五产品模型、Skill与Harness归因边界核对', '',
        f'作者：李明远。核对日期：{data["as_of"]}。本次为既有公共证据的离线审计，新增产品运行0次；S01五产品各3轮共15轮被复核，不重算成本周新增。', '',
        '当前证据支持端到端结果、具体请求边界和有限的产品内操作对照；五产品后台模型与完整Skill条件没有匹配，纯Harness因果分保持null。判断范围逐项列出，不能只靠报告末尾的限制说明。', '',
        '字段定位、源SHA、三轮配置与全部分母见[审计JSON](attribution-boundaries.json)和[逐产品评审记录](../'+ASSESSMENT+')。源文件固定为[b8cd4f9](https://github.com/llongwang751-arch/tx-harness/commit/'+BASELINE+')已有字节；当前官方配置说明不追认为旧实验已生效。', '',
        '| 产品 | 模型条件 | Skill条件 | 证据入口 |', '|---|---|---|---|']
    for row in data['products']:
        links = '、'.join(f'[r{r}](../public/supplements/contracts-v2/S01-{row["product_id"]}-r{r}/review.json)' for r in range(1,4))
        lines.append(f'| {row["name"]} | {row["model"]} | {row["skill"]} | {links} |')
    lines += ['', '## 全部尝试与条件分母', '',
        '下表每产品实际进入的S01任务均为3轮。单元格为“通过/eligible；未知；上游偏离”。未知和未进入条件不是产品失败；不得只保留形成正确请求的片段。请求能否形成本身可能受Harness影响，条件分母不是随机抽样，不能跨产品按这张表排名。', '',
        '| 产品 | 输入读取 | 缺失目标反馈 | literal写保真 |', '|---|---|---|---|']
    for row in data['products']:
        cells = [f'{m["passed"]}/{m["eligible"]}；未知{m["unknown_verdict"]}；偏离{m["upstream_deviation"]}' for m in row['s01_metrics']]
        lines.append('| '+row['name']+' | '+' | '.join(cells)+' |')
    lines += ['', '这些S01内部指标的环境有效性和适用性并未逐轮独立证明；JSON同时保留相应未证实计数。CLI/SDK命令、独立读取工具与GUI下载并非同一种工具契约。五产品S01均实际取得3份echo与3份receipt，字节/声明验收与内部请求证据分别报告。', '',
        '## 每款产品的结论与停止条件']
    for row in data['products']:
        lines += ['', '### '+row['name'], '', '**现象：**'+row['phenomenon'], '',
            '**原因线索：**'+row['cause_clue'], '', '**已验证结论：**'+row['validated_conclusion'], '',
            '**置信依据：**'+row['confidence_basis'], '', '**下一步：**'+row['next_action'], '',
            '**停止条件：**'+row['stop_condition']]
    lines += ['', '## 已完成的局部验证与仍未满足的控制', '',
        '[Codex三组权限对照](permission-pairs-v2.json)支持记录条件下的目标写入/拒绝；[WorkBuddy窗口v2](window-reopen-v2.md)支持续接前的原生消息与本地原件取回。它们不表示隐藏Skill、后台模型或工具实现已全部隔离，单对照也不足以估计普遍因果效应。', '',
        'DSH r2/r3确有Skill调用元数据；r2曾因事件投影意外暴露一份Skill正文，公开投影随后移除。不能声称评测方全程未接触Skill正文或已完成盲评；r3在审阅前排除了正文。这是评测过程限制，不作为产品失败或新运行。', '',
        '## 是否需要立即重跑五款', '',data['new_experiment_decision']['reason'], '',
        '只有取得能改变具体判断的新证据，才重新打开实验：', '']
    lines += [str(i)+'. '+s+'。' for i,s in enumerate(data['new_experiment_decision']['reopen_gate'],1)]
    lines += ['', '若官方允许替换模型适配器，可另登记确定性请求/响应的组件契约实验；它研究该受控入口，不把自建代理、模拟回合或另一API冒充原商业产品。当前未确认五产品都支持同一适配接口，不据此启动或声称完成这种实验。', '',
        '未来配置预检依据当前[官方OpenAI配置文档](https://learn.chatgpt.com/docs/config-file/config-reference)核对单项Skill开关，并按[Skill装载说明](https://learn.chatgpt.com/docs/build-skills)检查隐式调用及仓库、用户、管理和系统来源；配置选项存在不证明旧CLI已生效。产品运行与模型共同作用的评测边界参见[Anthropic方法说明](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)；可控条件分组与随机化参见[NIST实验设计](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)。这些来源提供方法，不代替本项目现场。', '',
        '复核：`python -X utf8 scripts/audit_attribution_boundaries.py --check`。该命令不启动产品，不修改旧包、旧分或已发周报；一致性检查不等于独立现场认证。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = build(read(ROOT/ASSESSMENT))
    outputs = {'reports/attribution-boundaries.json':json.dumps(data,ensure_ascii=False,indent=2)+'\n',
               'reports/attribution-boundaries.md':render(data)}
    for name, content in outputs.items():
        path=ROOT/name
        if args.check:
            require(path.read_text(encoding='utf-8')==content, 'Generated attribution audit drift: '+name)
        else:
            path.write_text(content,encoding='utf-8',newline='\n')
    print(json.dumps({'products':len(data['products']),'s01_old_runs_reviewed':15,
        'new_product_runs':0,'pure_harness_causal_score':None,
        'execute_new_experiment':data['new_experiment_decision']['execute_now']}))


if __name__ == '__main__':
    main()
