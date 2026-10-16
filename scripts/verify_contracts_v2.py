"""Verify published supplement packages and their deterministic coverage index."""
import argparse,json
from contract_v2 import ROOT,BASE,read,verify_public

def build():
    protocol=read(BASE/'protocol.json');rows=[]
    for spec in protocol['slots']:
        base=ROOT/'public/supplements/contracts-v2'/spec['slot_id']
        if not (base/'manifest.json').exists():
            rows.append({**spec,'public_state':'not_sealed','verification':None,'observations':None});continue
        result=verify_public(spec['slot_id']);review=read(base/'review.json')
        rows.append({**spec,'public_state':'sealed','verification':result,'observations':review['observations'],
            'base':base.relative_to(ROOT).as_posix(),'evidence_level':review['evidence_level'],
            'started_at':read(base/'execution-start.json')['started_at'],'end':read(base/'execution-end.json')})
    denominators=[]
    for card,product in sorted({(r['card'],r['product_id']) for r in rows}):
        planned=[r for r in rows if r['card']==card and r['product_id']==product]
        sealed=[r for r in planned if r['public_state']=='sealed']
        for metric in ('input_read','missing_feedback','write_fidelity','permission'):
            obs=[r['observations'][metric] for r in sealed]
            eligible=[o for o in obs if o.get('eligible') is True]
            passed=sum(o['verdict']=='pass' for o in eligible);failed=sum(o['verdict']=='fail' for o in eligible)
            unresolved=len(eligible)-passed-failed
            denominators.append({'card':card,'product_id':product,'metric':metric,'planned':len(planned),
                'public_started':len(sealed),'unsealed':len(planned)-len(sealed),
                'applicable_explicitly_verified':sum(o.get('applicable') is True for o in obs),
                'applicability_not_attested':sum(o.get('applicable') is not True and o['verdict']!='not_applicable' for o in obs),
                'not_applicable':sum(o['verdict']=='not_applicable' for o in obs),
                'eligible':len(eligible),'passed':passed,'failed':failed,'eligible_unresolved':unresolved,
                'upstream_deviation':sum(o['verdict']=='upstream_deviation' for o in obs),
                'unknown_verdict':sum(o['verdict']=='unknown' for o in obs),
                'environment_invalid_explicit':sum(r['end'].get('environment_invalid') is True for r in sealed),
                'environment_validity_not_attested':sum(not isinstance(r['end'].get('environment_invalid'),bool) for r in sealed),
                'ineligible_or_evidence_missing':sum(o.get('eligible') is not True and o['verdict']!='not_applicable' for o in obs),
                'conditional_pass_rate':passed/len(eligible) if eligible and not unresolved else None})
    return {'schema':'contract-v2-coverage','planned':len(rows),'public_sealed':sum(r['public_state']=='sealed' for r in rows),
        'rows':rows,'metric_denominators':denominators,'pure_harness_score':None,
        'limits':'Three variants and one requested configuration do not establish general reliability or matched backend weights. Missing evidence and unsealed slots are not failures.'}

def markdown(d):
    lines=['# 固定文件契约补测现场','',f"协议预先登记21位；当前公开封存{d['public_sealed']}/{d['planned']}。未封存不等于失败或未开始。旧31个pilot包和旧25组合另列，不混作独立重复。",'',
       'S01为五产品各三次固定读写/缺失文件反馈；S02为Codex三组允许/拒绝写权限配对。仅在实际目标操作出现时检查E1契约；GUI内部参数未知，保留E2。没有综合分或纯Harness排名。','',
       '| 实验位 | 公开状态 | echo原字节 | receipt声明 | 真实缺失读取反馈 | 写入/许可观察 |',
       '|---|---|---|---|---|---|']
    for r in d['rows']:
        if r['public_state']!='sealed':lines.append(f"| {r['slot_id']} | 未封存 | 未知 | 未知 | 未知 | 未知 |");continue
        v=r['verification'];o=r['observations'];fmt=lambda value:'通过' if value else '未通过/无文件'
        def verdict(name):
            item=o.get(name,{})
            return item.get('verdict','unknown') if isinstance(item,dict) else 'unknown'
        echo=fmt(v['echo_bytes_equal']) if v['echo_present'] else '未取得原件；字节未知'
        receipt=(fmt(v['receipt_declaration_valid'])+'（仅声明）') if v['receipt_present'] else '未取得原件；声明未知'
        if r['card']=='S02' and r['arm']=='deny':
            echo='有文件（核查许可）' if v['echo_present'] else '无文件（拒绝臂）'
            receipt='有文件（核查许可）' if v['receipt_present'] else '无文件（拒绝臂）'
        lines.append(f"| [{r['slot_id']}]({r['slot_id']}/README.md) | 已封存 | {echo} | {receipt} | {verdict('missing_feedback')} | {verdict('write_fidelity')} / {verdict('permission')} |")
    lines+=['','未取得原件不等于字节错误；应按普通输出卡、取回过程和逐包限制区分未交付与收集受阻。S02拒绝臂没有文件可能符合许可契约。产品自述not_found或external_actions=[]不证明实际工具错误/无外传；请按逐包事件和observations的具体定位复核。','',
       '逐指标分母见coverage.json的metric_denominators：计划、公开已启动、未封存、明确适用/适用未知、eligible、passed、failed、上游偏离、未知及明确环境无效分别列出。环境状态未明示不推定为有效；计时采集中断也不自动使已留存的每个工具事件无效。条件通过率只在eligible有已知判定时计算，eligible=0为null；同时保留进入该段之前的缺口。public_started只数已封存且可公开复核的真实提交，不推断未封存位尚未执行。','',
       'GUI选段的received_at是实际采集时刻；较早公开包的记录顺序可能按阅读段落排列，复核时间线应按received_at还原。当前导出器自动按该时刻排序；既有包不覆盖。','',
       '复核：`python -X utf8 scripts/verify_contracts_v2.py --check`。登记、输入、产物和投影SHA定位版本，仍依赖Operator采集，不是独立系统审计。','']
    return '\n'.join(lines)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    d=build();base=ROOT/'public/supplements/contracts-v2';base.mkdir(parents=True,exist_ok=True)
    js=json.dumps(d,ensure_ascii=False,indent=2)+'\n';md=markdown(d)
    if args.check:
        assert (base/'coverage.json').read_text(encoding='utf-8')==js,'coverage JSON drift'
        assert (base/'README.md').read_text(encoding='utf-8')==md,'coverage Markdown drift'
    else:
        (base/'coverage.json').write_text(js,encoding='utf-8',newline='\n');(base/'README.md').write_text(md,encoding='utf-8',newline='\n')
    print(json.dumps({'verified_public_slots':d['public_sealed'],'planned':d['planned'],'index_matches':True}))
if __name__=='__main__':main()
