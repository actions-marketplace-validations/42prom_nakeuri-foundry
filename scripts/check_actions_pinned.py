from pathlib import Path
import re,sys
bad=[];checked=0
roots=[Path('.github/workflows'),Path('templates/github'),Path('src/flutter_foundry/assets/github')]
for base in roots:
    if not base.exists(): continue
    for p in list(base.glob('*.yml'))+list(base.glob('*.yaml')):
        text=p.read_text(encoding='utf-8')
        for i,line in enumerate(text.splitlines(),1):
            m=re.search(r'uses:\s*([^\s]+)@([^\s#]+)',line)
            if not m: continue
            checked+=1
            if not re.fullmatch(r'[0-9a-fA-F]{40}',m.group(2)):
                bad.append(f'{p}:{i}: {m.group(0)}')
if bad:
    print('\n'.join(bad));sys.exit(1)
print(f'PASS: {checked} GitHub Actions references are pinned to full SHAs')
