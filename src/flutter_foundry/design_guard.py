from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from .util import safe_rel
RULES=[
 ('raw-color',re.compile(r'\bColor\(0x[0-9A-Fa-f]{8}\)')),
 ('raw-text-style',re.compile(r'\bTextStyle\(')),
 ('raw-border-radius',re.compile(r'BorderRadius\.circular\((?:\d+\.?\d*)\)')),
 ('raw-edge-insets',re.compile(r'EdgeInsets\.(?:all|symmetric|only)\([^\n]*(?:\d{1,3})')),
]
def scan_design(root:Path)->dict[str,Any]:
    findings=[];bases=[p for p in [root/'lib',root/'mobile'/'lib'] if p.exists()]
    for base in bases:
        for p in base.rglob('*.dart'):
            rel=safe_rel(p,root);norm='/'+rel.replace('\\','/')
            if '/design_system/' in norm or '/theme/' in norm:continue
            text=p.read_text(encoding='utf-8',errors='ignore')
            for rule,pat in RULES:
                for m in pat.finditer(text):findings.append({"severity":"medium","rule":rule,"path":rel,"line":text.count('\n',0,m.start())+1})
    return {"status":"warn" if findings else "pass","findings":findings,"summary":{"total":len(findings)}}
