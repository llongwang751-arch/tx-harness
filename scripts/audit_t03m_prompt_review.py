"""Check the draft prompt and run its synthetic cases against the pinned grader."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory

from audit_t03m_assisted_review import PIN, ROOT, adjudicate, read, replace_once, snapshot


REVIEW = ROOT / 'supplements/t03m-prompt-review-v1'
REFERENCE = 'supplements/behavior-protocol-v1/reference-outputs/T03-M'
STEP_PATH = 'steps/01_parsed_directive.json'


def prompt_revision(old):
    clause = next(line.removeprefix('> ') for line in (REVIEW / 'amendment.md').read_text(encoding='utf-8').splitlines()
                  if line.startswith('> '))
    lines = old.decode('utf-8').splitlines(keepends=True)
    offsets = [i for i, line in enumerate(lines) if line.startswith('1. ') and '`excluded_price_changes`' in line]
    if len(offsets) != 1:
        raise ValueError('Expected exactly one original instruction for C01.')
    lines.insert(offsets[0] + 1, f'   {clause}\n')
    return ''.join(lines).encode('utf-8')


def apply_example(outputs, change):
    kind = change['kind']
    if kind == 'none':
        return
    if kind == 'remove_publication_label':
        replace_once(outputs / 'bundle/announcement.md', '正式发布：'.encode('utf-8'), b'')
        return
    path = outputs / STEP_PATH
    value = read(path)
    row = next(item for item in value['excluded_price_changes'] if item['product_id'] == 'P-B')
    raw_reason = json.dumps(row['reason'], ensure_ascii=False).encode('utf-8')
    if kind == 'set_reason':
        new_reason = json.dumps(change['value'], ensure_ascii=False).encode('utf-8')
        replace_once(path, raw_reason, new_reason)
    elif kind == 'remove_reason':
        pattern = rb',[ \t]*\r?\n[ \t]*"reason":[ \t]*' + re.escape(raw_reason)
        match = re.search(pattern, path.read_bytes())
        if match is None:
            raise ValueError('Reference reason field layout differs from the registered fixture.')
        replace_once(path, match[0], b'')
    elif kind == 'reformat_step_json':
        path.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8'))
    else:
        raise ValueError(f'Unknown review example mutation: {kind}')


def audit(root):
    snapshot(root, extra_paths=(REFERENCE,))
    original = (root / 'cases/T03-M/prompt.md').read_bytes()
    draft = (REVIEW / 'prompt.md').read_bytes()
    if draft != prompt_revision(original):
        raise ValueError('Draft prompt differs from the pinned prompt with the proposed clause inserted.')
    examples = read(REVIEW / 'examples.json')['examples']
    seen, results = set(), []
    for index, example in enumerate(examples):
        if example['id'] in seen:
            raise ValueError(f'Duplicate example ID: {example["id"]}')
        seen.add(example['id'])
        output = root / f'example-{index}'
        shutil.copytree(root / REFERENCE, output)
        apply_example(output, example['change'])
        actual = adjudicate(root, output)
        selected = actual['selected_checks']
        row = {'c01': selected['T03M-C01']['passed'], 'c06': selected['T03M-C06']['passed'], 'score': actual['score']}
        if row != example['expected']:
            raise ValueError(f'{example["id"]}: expected {example["expected"]}, observed {row}')
        results.append({'id': example['id'], **row})
    return {'status': 'draft_for_review', 'grader_commit': PIN, 'draft_prompt_sha256': sha256(draft).hexdigest(),
            'examples_verified': len(results), 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='tx-t03m-prompt-review-') as folder:
        result = audit(Path(folder))
    if args.check and result != read(REVIEW / 'results.json'):
        raise ValueError('Stored example results differ from the pinned grader recheck.')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
