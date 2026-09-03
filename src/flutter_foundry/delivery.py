from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from .util import ASSET_ROOT
from .platform_adapters import detect_project_surfaces


def _ecosystems(surfaces: list[dict[str, Any]]) -> list[tuple[str,str]]:
    out=[]
    for s in surfaces:
        root='/' if s['root']=='.' else '/'+s['root']
        if s['id']=='flutter': out.append(('pub',root))
        elif s['id'] in {'node','nextjs'}: out.append(('npm',root))
        elif s['id']=='python': out.append(('pip',root))
        elif s['id']=='dotnet': out.append(('nuget',root))
        elif s['id']=='java': out.append(('maven',root))
    seen=[]
    for x in out:
        if x not in seen: seen.append(x)
    return seen


def install_delivery_plane(root: Path, force: bool = False) -> dict[str, Any]:
    root = root.resolve(); gh = root / ".github"; workflows = gh / "workflows"; workflows.mkdir(parents=True, exist_ok=True)
    surfaces=detect_project_surfaces(root)
    # Backward-compatible direct install on an empty target keeps the historical Flutter profile.
    if not surfaces:
        surfaces=[{'id':'flutter','root':'.','maturity':'flagship','manifests':[]}]
    created=[]
    mapping={ASSET_ROOT/"github"/"foundry-governance.yml":workflows/"foundry-governance.yml"}
    if any(s['id']=='flutter' for s in surfaces):
        mapping.update({
            ASSET_ROOT / "github" / "flutter-pr-ci.yml": workflows / "flutter-pr-ci.yml",
            ASSET_ROOT / "github" / "release-gate.yml": workflows / "release-gate.yml",
            ASSET_ROOT / "github" / "flutter-e2e.yml": workflows / "flutter-e2e.yml",
            ASSET_ROOT / "github" / "ios-compile.yml": workflows / "ios-compile.yml",
        })
    missing=[str(src) for src in mapping if not src.exists()]
    if missing:return {"status":"fail","created":[],"missing_assets":missing}
    for src,dst in mapping.items():
        if force or not dst.exists():shutil.copy2(src,dst);created.append(str(dst.relative_to(root)))
    pr=gh/"pull_request_template.md"
    if force or not pr.exists():
        pr.write_text("""## Intent\n\n## Requirements / invariant IDs\n\n## What changed\n\n## What must not change\n\n## Cross-surface contracts\n- [ ] API/schema/client compatibility checked when applicable\n\n## Evidence\n- [ ] native format/analyze/tests for affected surfaces\n- [ ] Foundry deterministic gates\n- [ ] runtime/E2E when risk requires\n- [ ] independent review when risk requires\n- [ ] proof bundle\n\n## Simplification check\nCould this be materially simpler without losing correctness, security or testability?\n""",encoding="utf-8");created.append(str(pr.relative_to(root)))
    owners=gh/"CODEOWNERS"
    if force or not owners.exists():owners.write_text("# Replace before branch protection is enabled\n* @OWNER_PLACEHOLDER\n",encoding="utf-8");created.append(str(owners.relative_to(root)))
    dep=gh/"dependabot.yml"
    if force or not dep.exists():
        lines=['version: 2','updates:']
        for ecosystem,directory in _ecosystems(surfaces)+[('github-actions','/')]:
            lines += [f'  - package-ecosystem: {ecosystem}',f'    directory: {directory}','    schedule: {interval: weekly}']
        dep.write_text('\n'.join(lines)+'\n',encoding='utf-8');created.append(str(dep.relative_to(root)))
    return {
      "status":"pass","created":created,"surfaces":surfaces,
      "required_repo_variables":["FOUNDRY_INSTALL_SPEC"] + (["FLUTTER_GIT_REF"] if any(s['id']=='flutter' for s in surfaces) else []),
      "warning":"Set immutable toolchain references and replace CODEOWNERS placeholder before protected-branch enforcement. Framework delivery remains adapter-specific."
    }
