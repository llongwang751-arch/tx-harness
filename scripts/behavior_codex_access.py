"""Check real file access under the Codex Windows profile used for task tools."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from harness_eval.core import ROOT, sha256, write_json


def sandbox_config(argv):
    return [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == '-c']


def protected_files(case):
    return {
        'grader': ROOT / 'evaluation_v3/grader.py',
        'rubric': ROOT / 'config/rubric.json',
        'oracle': ROOT / f'cases/{case}/oracle.json',
        'reference': ROOT / f'supplements/behavior-protocol-v1/reference-outputs/{case}/summary.json'
        if case == 'T05-M' else ROOT / f'cases/{case}/expected/bundle/announcement.md',
    }


def program(expected, targets):
    def quoted(text):
        return "'" + str(text).replace("'", "''") + "'"

    inputs = ','.join(quoted(name) for name in expected)
    targets = ';'.join(f'{key}={quoted(value)}' for key, value in targets.items())
    return f'''$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$hashes = @{{}}
foreach($rel in @({inputs})) {{
    $hashes[$rel] = (Get-FileHash -LiteralPath $rel -Algorithm SHA256).Hash.ToLowerInvariant()
}}
$observations = @{{}}
$targets = @{{{targets}}}
foreach($label in $targets.Keys) {{
    try {{
        $opened = [IO.File]::OpenRead($targets[$label])
        $opened.Dispose()
        $observations[$label] = 'readable'
    }} catch {{
        $cause = $_.Exception
        while($cause.InnerException) {{ $cause = $cause.InnerException }}
        if($cause -is [UnauthorizedAccessException]) {{
            $observations[$label] = 'denied:' + $cause.HResult.ToString('X8')
        }} else {{
            $observations[$label] = $cause.GetType().Name
        }}
    }}
}}
[ordered]@{{schema='codex-access-check/v1'; input_sha256=$hashes; protected_open=$observations}} | ConvertTo-Json -Compress
'''


def validate_observation(observed, expected, targets):
    if observed.get('schema') != 'codex-access-check/v1' or observed.get('input_sha256') != expected:
        raise ValueError('Access probe did not verify the exact input and prompt hashes.')
    if observed.get('protected_open') != {name: 'denied:80070005' for name in targets}:
        raise ValueError('Access probe could not establish Windows access denied for every protected file.')


def probe(executable, args, workspace, expected, case, evidence, environment):
    if os.name != 'nt':
        raise ValueError('The registered access profile requires Windows Codex CLI.')
    targets = protected_files(case)
    # A protected target must be a real file readable by the evaluator before
    # an access-denied status from the participant process can be meaningful.
    target_hashes = {label: sha256(path) for label, path in targets.items()}
    source = program(expected, targets)
    (evidence / 'access-probe.ps1').write_text(source, encoding='utf-8', newline='\n')
    options = sandbox_config(args)
    config_args = [part for option in options for part in ('-c', option)]
    shell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    encoded = base64.b64encode(source.encode('utf-16-le')).decode('ascii')
    started = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix='codex-probe-config-') as config_home:
        proc = subprocess.run([str(executable), 'sandbox', '--cd', str(workspace),
                               '--permission-profile', 'harness_pilot', *config_args,
                               '--', str(shell), '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                              cwd=workspace, env={**environment, 'CODEX_HOME': config_home},
                              capture_output=True, timeout=35)
    (evidence / 'access.stdout.jsonl').write_bytes(proc.stdout)
    (evidence / 'access.stderr.txt').write_bytes(proc.stderr)
    if proc.returncode:
        raise ValueError(f'Native sandbox access probe exited {proc.returncode}. Original streams retained.')
    observation = json.loads(proc.stdout.decode('utf-8-sig'))
    validate_observation(observation, expected, targets)
    result = {
        'schema': 'tx-harness/codex-native-access/v1',
        'started_at': started,
        'ended_at': datetime.now(timezone.utc).isoformat(),
        'transport': 'codex sandbox with task permissions and empty user config',
        'exit_code': proc.returncode,
        'executable_sha256': sha256(executable),
        'config_sha256': hashlib.sha256(json.dumps(options, ensure_ascii=False).encode()).hexdigest(),
        'protected_files': {label: {'path': path.relative_to(ROOT).as_posix(), 'host_sha256': target_hashes[label]}
                            for label, path in targets.items()},
        'stdout_sha256': hashlib.sha256(proc.stdout).hexdigest(),
        'observation': observation,
    }
    write_json(evidence / 'access.json', result)
    return result


def native_command_observation(path, expected):
    """Require the real shell tool's output rather than an agent-message assertion."""
    observed = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        row = json.loads(line)
        item = row.get('item', {})
        if row.get('type') != 'item.completed' or item.get('type') != 'command_execution':
            continue
        if (item.get('exit_code') != 0 or 'Get-FileHash' not in item.get('command', '')
                or 'ConvertTo-Json' not in item.get('command', '')):
            continue
        for output_line in item.get('aggregated_output', '').splitlines():
            if not output_line.startswith('{'):
                continue
            result = json.loads(output_line)
            if result == expected:
                observed.append(result)
    if len(observed) != 1:
        raise ValueError(f'Expected one successful native access observation, got {len(observed)}.')
    return observed[0]
