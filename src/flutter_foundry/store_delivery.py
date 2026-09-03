from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

PLACEHOLDERS = {"", "FILL_ME", "TODO", "TBD", "OWNER_PLACEHOLDER"}
TRACKS = {"internal", "alpha", "beta", "production"}


def init_store_delivery(root: Path, force: bool = False) -> Path:
    p = root.resolve() / ".factory" / "store-delivery.json"
    if p.exists() and not force:
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "foundry/store-delivery/v1",
        "android": {
            "enabled": False,
            "package_name": "FILL_ME",
            "track": "internal",
            "rollout_fraction": 1.0,
            "credential_env": "PLAY_SERVICE_ACCOUNT_JSON",
            "aab_path": "build/app/outputs/bundle/release/app-release.aab",
        },
        "ios": {
            "enabled": False,
            "app_identifier": "FILL_ME",
            "ipa_path": "build/ios/ipa/app.ipa",
            "key_id_env": "ASC_KEY_ID",
            "issuer_id_env": "ASC_ISSUER_ID",
            "key_content_env": "ASC_KEY_CONTENT",
            "skip_waiting_for_build_processing": True,
        },
    }
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def _placeholder(value: Any) -> bool:
    return value is None or str(value).strip() in PLACEHOLDERS


def _safe_env_name(value: str) -> bool:
    return bool(value) and value.replace("_", "A").isalnum() and value.upper() == value


def validate_store_delivery(root: Path) -> dict[str, Any]:
    p = root.resolve() / ".factory" / "store-delivery.json"
    if not p.exists():
        return {"status": "fail", "findings": ["store delivery contract missing"]}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "fail", "findings": [f"invalid store delivery contract: {exc}"]}
    findings: list[str] = []
    if data.get("schema") != "foundry/store-delivery/v1":
        findings.append("unsupported store delivery schema")
    android = data.get("android", {})
    if android.get("enabled"):
        if _placeholder(android.get("package_name")): findings.append("android.package_name is not configured")
        if android.get("track") not in TRACKS: findings.append("android.track is invalid")
        try:
            rollout = float(android.get("rollout_fraction"))
            if not (0 < rollout <= 1): findings.append("android.rollout_fraction must be >0 and <=1")
        except Exception:
            findings.append("android.rollout_fraction must be numeric")
        if not _safe_env_name(str(android.get("credential_env", ""))): findings.append("android.credential_env must be an uppercase environment variable name")
        if _placeholder(android.get("aab_path")): findings.append("android.aab_path is not configured")
    ios = data.get("ios", {})
    if ios.get("enabled"):
        if _placeholder(ios.get("app_identifier")): findings.append("ios.app_identifier is not configured")
        if _placeholder(ios.get("ipa_path")): findings.append("ios.ipa_path is not configured")
        for field in ["key_id_env", "issuer_id_env", "key_content_env"]:
            if not _safe_env_name(str(ios.get(field, ""))): findings.append(f"ios.{field} must be an uppercase environment variable name")
    if not android.get("enabled") and not ios.get("enabled"):
        findings.append("no store delivery target is enabled")
    return {"status": "fail" if findings else "pass", "findings": findings, "path": str(p), "config": data}


def _fastlane_prefix(root: Path) -> list[str] | None:
    if (root / "Gemfile").exists() and shutil.which("bundle"):
        return ["bundle", "exec", "fastlane"]
    if shutil.which("fastlane"):
        return ["fastlane"]
    return None


def store_delivery_preflight(root: Path, platform_name: str) -> dict[str, Any]:
    root = root.resolve(); platform_name = platform_name.lower()
    check = validate_store_delivery(root)
    findings = list(check.get("findings", []))
    if platform_name not in {"android", "ios"}:
        return {"status": "fail", "findings": ["platform must be android or ios"]}
    config = check.get("config", {}).get(platform_name, {})
    if not config.get("enabled"):
        findings.append(f"{platform_name} store delivery is not enabled")
    artifact_key = "aab_path" if platform_name == "android" else "ipa_path"
    artifact = root / str(config.get(artifact_key, ""))
    if config.get("enabled") and not artifact.is_file():
        findings.append(f"release artifact missing: {artifact_key}={artifact}")
    prefix = _fastlane_prefix(root)
    if prefix is None:
        findings.append("fastlane is unavailable (install fastlane or configure Bundler/Gemfile)")
    env_names = []
    if platform_name == "android": env_names = [config.get("credential_env")]
    else: env_names = [config.get("key_id_env"), config.get("issuer_id_env"), config.get("key_content_env")]
    missing_env = [str(name) for name in env_names if name and not os.getenv(str(name))]
    if missing_env:
        findings.append(f"credential environment variables missing: {', '.join(missing_env)}")
    if platform_name == "ios" and platform.system() != "Darwin":
        findings.append("iOS TestFlight delivery is restricted to macOS in Foundry's default high-assurance profile")
    return {
        "status": "fail" if findings else "pass",
        "findings": findings,
        "platform": platform_name,
        "artifact": str(artifact),
        "fastlane_prefix": prefix,
        "credential_env_names": env_names,
        "rule": "credential values are read only at execution time and never stored in the repository",
    }


def execute_store_delivery(root: Path, platform_name: str, approved: bool = False, timeout: int = 1800) -> dict[str, Any]:
    """Execute an explicitly approved store upload without persisting raw credentials."""

    if not approved:
        return {"status": "blocked", "reason": "explicit approval is required for store delivery"}
    root = root.resolve(); platform_name = platform_name.lower()
    pre = store_delivery_preflight(root, platform_name)
    if pre.get("status") != "pass":
        return {"status": "blocked", "reason": "preflight failed", "preflight": pre}
    data = json.loads((root / ".factory" / "store-delivery.json").read_text(encoding="utf-8"))
    cfg = data[platform_name]; prefix = pre["fastlane_prefix"]
    assert prefix
    secret_file: Path | None = None
    try:
        if platform_name == "android":
            raw = os.environ[cfg["credential_env"]]
            fd, name = tempfile.mkstemp(prefix="foundry-play-", suffix=".json")
            os.close(fd); secret_file = Path(name)
            secret_file.write_text(raw, encoding="utf-8")
            secret_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            cmd = prefix + [
                "supply", "--aab", str((root / cfg["aab_path"]).resolve()),
                "--package_name", cfg["package_name"], "--track", cfg["track"],
                "--rollout", str(cfg["rollout_fraction"]), "--json_key", str(secret_file),
                "--skip_upload_metadata", "true", "--skip_upload_images", "true",
                "--skip_upload_screenshots", "true", "--skip_upload_changelogs", "true",
            ]
        else:
            key_payload = {
                "key_id": os.environ[cfg["key_id_env"]],
                "issuer_id": os.environ[cfg["issuer_id_env"]],
                "key": os.environ[cfg["key_content_env"]],
            }
            fd, name = tempfile.mkstemp(prefix="foundry-asc-", suffix=".json")
            os.close(fd); secret_file = Path(name)
            secret_file.write_text(json.dumps(key_payload), encoding="utf-8")
            secret_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            cmd = prefix + [
                "pilot", "upload", "--ipa", str((root / cfg["ipa_path"]).resolve()),
                "--app_identifier", cfg["app_identifier"], "--api_key_path", str(secret_file),
            ]
            if cfg.get("skip_waiting_for_build_processing", True):
                cmd.append("--skip_waiting_for_build_processing")
        p = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=timeout)
        return {
            "status": "pass" if p.returncode == 0 else "fail",
            "platform": platform_name,
            "returncode": p.returncode,
            "stdout": p.stdout[-12000:],
            "stderr": p.stderr[-12000:],
            "command_summary": ["bundle exec fastlane" if prefix[:2] == ["bundle", "exec"] else "fastlane", "supply" if platform_name == "android" else "pilot upload"],
        }
    except subprocess.TimeoutExpired:
        return {"status": "fail", "platform": platform_name, "reason": f"store delivery timed out after {timeout}s"}
    finally:
        if secret_file is not None:
            try: secret_file.unlink()
            except FileNotFoundError: pass
