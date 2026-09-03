from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from .util import safe_rel

def scan_test_quality(root:Path)->dict[str,Any]:
    findings=[]; tests=[]
    for base in [root/'test',root/'integration_test',root/'mobile'/'test',root/'mobile'/'integration_test']:
        if not base.exists(): continue
        for p in base.rglob('*.dart'):
            text=p.read_text(encoding='utf-8',errors='ignore'); rel=safe_rel(p,root); tests.append(rel)
            if re.search(r'test(?:Widgets)?\(',text) and not re.search(r'\bexpect\s*\(',text): findings.append({"severity":"high","rule":"test-without-assertion","path":rel})
            if text.count('Mock')+text.count('when(')>20: findings.append({"severity":"medium","rule":"excessive-mocking","path":rel})
            if 'skip: true' in text or 'skip:true' in text: findings.append({"severity":"medium","rule":"skipped-test","path":rel})
    return {"status":"fail" if any(f['severity']=='high' for f in findings) else "warn" if findings else "pass","findings":findings,"tests_seen":len(tests),"note":"Static test-value heuristics; high-risk workflows should add mutation/property/contract tests in CI."}
