"""Preregistered checks for direct native UI retrieval and window closure v2.

UI provenance is collected by the operator. This module checks custody and
event order; it cannot independently authenticate a screenshot or exclude
unexposed background model/Skill activity.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path


def instant(text):
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise ValueError('Need timezone-aware observation time')
    return value


def close_verdict(proof):
    rows = proof.get('observations', [])
    if len(rows) < 2 or len(rows) > 8:
        return False
    if not proof.get('before_windows'):
        return False
    if [r['sequence'] for r in rows] != list(range(1, len(rows)+1)):
        return False
    start = instant(proof['close_started_at'])
    last = start
    for row in rows:
        at = instant(row['at'])
        if at < last or (at-start).total_seconds() > 30:
            return False
        last = at
    if rows[-1]['windows'] or rows[-2]['windows']:
        return False
    launch = instant(proof['launch_at'])
    return last <= launch and launch <= instant(proof['restored_at']) and proof.get('same_task') is True


def direct_verdict(probe: bytes, directory: Path, receipts):
    required = {'retrieval-before/probe.txt', 'retrieval-before/stage-a.txt',
                'retrieval-after/probe.txt', 'retrieval-after/stage-a.txt'}
    rows = {row['relative_path']: row for row in receipts}
    if set(rows) != required or len(receipts) != len(required):
        return False
    expected = hashlib.sha256(probe).hexdigest()
    for name, row in rows.items():
        if row.get('method') != 'native_ui_save_as' or not row.get('source_scene') or not row.get('destination_scene'):
            return False
        path = directory / name
        if not path.is_file() or path.read_bytes() != probe:
            return False
        if row['sha256'] != expected or row['bytes'] != len(probe):
            return False
        if row['source_role'] != ('original_message_attachment' if name.endswith('/probe.txt') else 'native_stage_a_card'):
            return False
        instant(row['at'])
    return True


def time_verdict(checkpoint, continuation):
    observed = (instant(continuation['before_at'])-instant(checkpoint['at'])).total_seconds()
    return abs(observed-180) <= 15 and abs(observed-continuation['delay_seconds']) < 1
