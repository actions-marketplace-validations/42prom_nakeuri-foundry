from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from .flutter_stack import official_stack_status

ACTION_RE=re.compile(r'uses:\s*([^\s]+)@([^\s#]+)')
FULL_SHA=re.compile(r'^[0-9a-fA-F]{40}$')


def scan_supply_chain(root: Path, release: bool=False) -> dict[str,Any]:
    root=root.resolve();findings=[]
    pubspec=next((p for p in [root/'pubspec.yaml',root/'mobile'/'pubspec.yaml'] if p.exists()),None)
    if pubspec:
        lock=pubspec.parent/'pubspec.lock'
        if release and not lock.exists():findings.append({'severity':'high','rule':'missing-pubspec-lock','path':str(lock.relative_to(root))})
        text=pubspec.read_text(encoding='utf-8',errors='ignore').splitlines()
        for i,line in enumerate(text):
            if re.match(r'^\s+git:\s*(?:$|https?://|git@)',line):
                indent=len(line)-len(line.lstrip());window=text[i:i+8]
                if not any((len(x)-len(x.lstrip())>indent and re.match(r'^\s+ref:\s*[0-9a-fA-F]{40}\s*$',x)) for x in window[1:]):
                    findings.append({'severity':'high' if release else 'medium','rule':'git-dependency-not-full-sha-pinned','path':str(pubspec.relative_to(root)),'line':i+1})
    for base in [root/'.github/workflows']:
        if not base.exists():continue
        for p in list(base.glob('*.yml'))+list(base.glob('*.yaml')):
            for i,line in enumerate(p.read_text(encoding='utf-8',errors='ignore').splitlines(),1):
                m=ACTION_RE.search(line)
                if m and not FULL_SHA.fullmatch(m.group(2)):
                    findings.append({'severity':'high','rule':'github-action-not-full-sha-pinned','path':str(p.relative_to(root)),'line':i,'action':m.group(1)})
    stack=official_stack_status(root)
    if stack['official_skills_present'] and not stack['skills_lock_valid']:
        findings.append({'severity':'high' if release else 'medium','rule':'official-skills-unlocked-or-drifted','path':'.agents/skills'})
    high=sum(f['severity']=='high' for f in findings)
    return {'status':'fail' if high else 'warn' if findings else 'pass','findings':findings,'release_mode':release,'summary':{'total':len(findings),'high':high}}
