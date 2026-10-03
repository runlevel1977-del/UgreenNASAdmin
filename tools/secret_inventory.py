#!/usr/bin/env python3
"""Read-only inventory of known settings copies; never queries a credential vault."""
import argparse
import json
import os
from pathlib import Path

NAMES = ('app_settings.json', 'nas_admin_connection.json', 'telegram_notify.json',
         'nas_watch_local.json', 'nas_daily_report_local.json', 'qnap_smb_prefs.json')
FIELDS = frozenset(('password', 'ssh_key_passphrase', 'bot_token', 'smtp_pass', 'smtp_password'))


def summarize(value):
    counts = {'plaintext_fields': 0, 'vault_references': 0}
    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in FIELDS and child:
                    if isinstance(child, dict) and set(child) == {'$ugreen_secret'}:
                        counts['vault_references'] += 1
                    elif isinstance(child, str):
                        counts['plaintext_fields'] += 1
                visit(child)
        elif isinstance(item, list):
            for child in item: visit(child)
    visit(value)
    return counts


def inventory(directory):
    root = Path(directory).resolve(strict=True)
    findings = []; visited = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(parent)/d).is_symlink()
                         and d not in ('.git', '__pycache__') and len((Path(parent)/d).relative_to(root).parts) <= 10)
        for name in sorted(files):
            visited += 1
            if visited > 10000: raise ValueError('Inventory exceeds 10000 files; select a narrower directory')
            lower = name.lower()
            if not any(lower == base or lower.startswith(base + '.') for base in NAMES): continue
            path = Path(parent)/name
            result = {'file': path.relative_to(root).as_posix()}
            try:
                if path.is_symlink() or not path.is_file(): raise ValueError('unsafe file type')
                with path.open('rb') as stream: data = stream.read(2*1024*1024+1)
                if len(data) > 2*1024*1024: raise ValueError('size limit')
                result.update(summarize(json.loads(data)))
                result['status'] = 'review-plaintext' if result['plaintext_fields'] else 'no-plaintext-in-known-fields'
            except Exception as exc:
                result['status'] = 'unreadable-or-unsupported'
                result['error_type'] = type(exc).__name__
            findings.append(result)
    return {'schema': 1, 'files': findings,
            'scope': 'Known filenames/fields only; no vault access, deletion, migration, log-content scan or proof of absence'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args.directory), indent=2))
