"""Check the public, bounded native-interface preflight without launching apps."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'public/supplements/gui-controls-v1'

def main():
    manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    if manifest['actual_task_runs'] != 0:
        raise ValueError('Settings inspection cannot be counted as product task runs')
    expected=set()
    for record in manifest['files']:
        name=record['path']
        if '/' in name or '\\' in name or name in {'.','..','manifest.json'}:
            raise ValueError('Unsafe preflight manifest path')
        data=(BASE/name).read_bytes()
        if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:
            raise ValueError('Preflight bytes changed: '+name)
        if name in expected: raise ValueError('Duplicate source')
        expected.add(name)
        if name.endswith('.jpg') and not data.startswith(b'\xff\xd8\xff'):
            raise ValueError('Native screenshot format differs')
    actual={x.name for x in BASE.iterdir() if x.is_file() and x.name!='manifest.json'}
    if actual!=expected: raise ValueError('Unmanifested preflight source')
    raw=(BASE/'observations.json').read_text(encoding='utf-8')
    for private_label in ('wbSeedToken','accountSnapshot','Device id:', 'Authorization: Bearer'):
        if private_label in raw: raise ValueError('Unreviewed account/context field in preflight')
    observations=json.loads(raw)
    products={x['id']:x for x in observations['products']}
    if set(products)!={'workbuddy','yuanbao','doubao'}: raise ValueError('Need the three requested surfaces')
    for id in ('yuanbao','doubao'):
        if products[id]['actual_new_tasks']!=0:
            raise ValueError('Menu inspection is not a new task')
        for key in ('next_action','stop_condition','confidence','judgment'):
            if not products[id].get(key): raise ValueError('Unmanaged feasibility unknown')
    if products['doubao']['surface']!='工作任务 → 云电脑' or products['doubao']['saved_connector'] is not False:
        raise ValueError('Cloud preflight cannot silently become local integration')
    if not any('自定义连接器仅支持在本地电脑中使用' in line
               for row in observations['reviewed_excerpts'] for line in row['lines']):
        raise ValueError('Local-only claim lacks its literal source')
    for row in observations['reviewed_excerpts']:
        if len(row['private_original_sha256'])!=64 or not row['lines'] or not row['disclosure']:
            raise ValueError('Unbound reviewed excerpt')
    for product in products.values():
        for image in product['images']:
            if image not in expected: raise ValueError('Missing interface screenshot')
    print(json.dumps({'surfaces':3,'preflight_task_runs':0,'manifested_files':len(expected)}))

if __name__=='__main__': main()
