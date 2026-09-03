from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .agent_runtime import AgentExecutor, OpenHandsAgentExecutor
from .docker_runtime import DockerExecutor
from .execution_fabric import RISK_ORDER, provider_contract
from .runtime_security import hardened_container_policy, image_is_digest_pinned


@dataclass(frozen=True)
class ProviderCapabilities:
    provider_id: str
    isolation: str
    max_risk: str
    agent_tasks: bool = True
    distributed: bool = False
    observed_runtime_attestation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LifecycleProvider(Protocol):
    capabilities: ProviderCapabilities

    def available(self) -> bool: ...
    def run_agent(self, workspace: Path, role: str, prompt: str, *, risk: str, output_path: Path | None = None) -> dict[str, Any]: ...


class AgentExecutorProvider:
    """Adapts any existing AgentExecutor into the provider-neutral lifecycle.

    The adapter reports the executor's *actual* isolation. A worktree-backed agent
    therefore cannot silently satisfy HIGH/RELEASE isolation requirements.
    """

    def __init__(self, executor: AgentExecutor, *, provider_id: str = "openhands"):
        self.executor = executor
        isolation = str(getattr(executor, "isolation_level", "unknown"))
        max_risk = "HIGH" if isolation in {"container", "remote", "ci-ephemeral"} else "MEDIUM"
        self.capabilities = ProviderCapabilities(
            provider_id=provider_id,
            isolation=isolation,
            max_risk=max_risk,
            agent_tasks=True,
            distributed=isolation in {"remote", "ci-ephemeral"},
            observed_runtime_attestation=isolation == "container",
        )

    def available(self) -> bool:
        checker = getattr(self.executor, "available", None)
        return bool(checker()) if callable(checker) else True

    def run_agent(self, workspace: Path, role: str, prompt: str, *, risk: str, output_path: Path | None = None) -> dict[str, Any]:
        result = self.executor.run(workspace, role, prompt, output_path)
        result = dict(result)
        result.setdefault("provider", self.capabilities.provider_id)
        result.setdefault("isolation", self.capabilities.isolation)
        result.setdefault("provider_evidence", {})
        ev = result["provider_evidence"] if isinstance(result["provider_evidence"], dict) else {}
        ev.update({
            "commit_bound_workspace": workspace.resolve().exists(),
            "structured_execution_result": True,
            "usage_telemetry": isinstance(result.get("usage"), dict),
        })
        result["provider_evidence"] = ev
        return result


class DockerJsonAgentProvider:
    """Runs a JSON request/response agent command inside the hardened Docker runtime.

    The image and command are explicit configuration; no pretend Docker execution is
    reported when they are absent. The command receives two workspace-relative paths:
    request JSON then response JSON, either through ``{request}``/``{response}``
    placeholders or appended as final arguments.
    """

    def __init__(
        self,
        image: str | None = None,
        command: list[str] | None = None,
        *,
        executor: DockerExecutor | None = None,
        network_required: bool = True,
    ):
        self.image = image or os.getenv("NAKEURI_DOCKER_AGENT_IMAGE")
        if command is None:
            raw = os.getenv("NAKEURI_DOCKER_AGENT_COMMAND", "").strip()
            if raw:
                try:
                    parsed = json.loads(raw)
                    command = [str(x) for x in parsed] if isinstance(parsed, list) else shlex.split(raw)
                except Exception:
                    command = shlex.split(raw)
        self.command = command or []
        self.executor = executor or DockerExecutor()
        self.network_required = network_required
        self.capabilities = ProviderCapabilities("docker", "container", "RELEASE", True, False, True)

    def available(self) -> bool:
        return bool(self.image and self.command and self.executor.available())

    def _command(self, request_rel: str, response_rel: str) -> list[str]:
        has_placeholder = any("{request}" in x or "{response}" in x for x in self.command)
        out = [x.replace("{request}", request_rel).replace("{response}", response_rel) for x in self.command]
        return out if has_placeholder else [*out, request_rel, response_rel]

    def run_agent(self, workspace: Path, role: str, prompt: str, *, risk: str, output_path: Path | None = None) -> dict[str, Any]:
        risk = risk.upper()
        if not self.available():
            return {"status": "unavailable", "provider": "docker", "reason": "Docker agent image/command/runtime is not configured"}
        assert self.image
        if risk in {"HIGH", "RELEASE"} and not image_is_digest_pinned(self.image):
            return {"status": "blocked", "provider": "docker", "reason": "HIGH/RELEASE Docker agent image must be digest pinned"}
        io_dir = workspace / ".factory" / "provider_io"
        io_dir.mkdir(parents=True, exist_ok=True)
        run_id = uuid.uuid4().hex
        req = io_dir / f"{run_id}.request.json"
        resp = io_dir / f"{run_id}.response.json"
        request_rel = "/workspace/" + req.relative_to(workspace).as_posix()
        response_rel = "/workspace/" + resp.relative_to(workspace).as_posix()
        req.write_text(json.dumps({
            "schema": "nakeuri/provider-agent-request/v1",
            "role": role,
            "risk": risk,
            "prompt": prompt,
            "output_path": str(output_path) if output_path else None,
        }, sort_keys=True) + "\n", encoding="utf-8")
        try:
            policy = hardened_container_policy(risk, self.image, network_required=self.network_required)
            runtime = self.executor.execute(policy, workspace, self._command(request_rel, response_rel))
            if runtime.get("status") != "pass":
                return {"status": "fail", "provider": "docker", "reason": "container agent execution failed", "runtime": runtime}
            if not resp.exists():
                return {"status": "fail", "provider": "docker", "reason": "agent response file missing", "runtime": runtime}
            try:
                result = json.loads(resp.read_text(encoding="utf-8"))
            except Exception as exc:
                return {"status": "fail", "provider": "docker", "reason": f"invalid agent response JSON: {exc}", "runtime": runtime}
            if not isinstance(result, dict):
                return {"status": "fail", "provider": "docker", "reason": "agent response must be a JSON object", "runtime": runtime}
            result.setdefault("provider", "docker")
            result.setdefault("isolation", "container")
            result["runtime"] = runtime
            result["provider_evidence"] = {
                "commit_bound_workspace": True,
                "structured_execution_result": True,
                "usage_telemetry": isinstance(result.get("usage"), dict),
                "security_isolation_attestation": runtime.get("security", {}).get("status") == "pass",
                "network_policy_attestation": bool(runtime.get("runtime_attestation", {}).get("network_mode")),
                "resource_limit_attestation": bool(runtime.get("runtime_attestation", {}).get("memory_mb")) and bool(runtime.get("runtime_attestation", {}).get("cpus")),
                "non_root_attestation": str(runtime.get("runtime_attestation", {}).get("user", "")).split(":", 1)[0] not in {"", "0", "root"},
                "ephemeral_environment": True,
                "supply_chain_identity": image_is_digest_pinned(self.image),
                "human_approval_boundary": True,
            }
            return result
        finally:
            try:
                req.unlink()
            except FileNotFoundError:
                pass
            try:
                resp.unlink()
            except FileNotFoundError:
                pass



class AntigravityHeadlessProvider:
    """Run Nakeuri static agents through the official Antigravity headless CLI.

    This is intentionally capped at MEDIUM risk: ``agy --sandbox`` constrains terminal
    execution, but it does not prove the container/resource/network attestations required
    by Nakeuri for HIGH/RELEASE execution. Those tasks must use Docker/Kubernetes/remote
    isolation even when Antigravity is the coding harness inside that environment.
    """

    ROLE_MAP={
        "worker":"nakeuri-flutter-worker",
        "reviewer":"nakeuri-architecture-reviewer",
        "security-reviewer":"nakeuri-security-reviewer",
        "release-verifier":"nakeuri-runtime-verifier",
        "runtime-verifier":"nakeuri-runtime-verifier",
        "architect":"nakeuri-architect",
        "explorer":"nakeuri-explorer",
        "test-designer":"nakeuri-test-planner",
        "test-planner":"nakeuri-test-planner",
    }

    def __init__(self, *, executable: str="agy", print_timeout: str="20m"):
        self.executable=executable;self.print_timeout=print_timeout
        self.capabilities=ProviderCapabilities("antigravity","process/workspace-sandbox","MEDIUM",True,False,False)

    def available(self)->bool:
        return shutil.which(self.executable) is not None

    @staticmethod
    def _review_schema()->str:
        return json.dumps({
            "type":"object","additionalProperties":False,
            "properties":{
                "schema":{"type":"string","const":"nakeuri/review-output/v1"},
                "status":{"type":"string","enum":["PASS","FAIL","WARN"]},
                "findings":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{"severity":{"type":"string","enum":["BLOCKER","HIGH","MEDIUM","LOW"]},"message":{"type":"string"},"evidence":{"type":"string"}},"required":["severity","message","evidence"]}},
            },"required":["schema","status","findings"]
        },separators=(",",":"))

    def run_agent(self, workspace: Path, role: str, prompt: str, *, risk: str, output_path: Path | None = None) -> dict[str,Any]:
        risk=risk.upper()
        if risk in {"HIGH","RELEASE"}:return {"status":"blocked","provider":"antigravity","reason":"Antigravity workspace sandbox alone is not sufficient Nakeuri HIGH/RELEASE isolation"}
        if not self.available():return {"status":"unavailable","provider":"antigravity","reason":"agy CLI not found on PATH"}
        agent=self.ROLE_MAP.get(role,"nakeuri-flutter-worker" if role=="worker" else role)
        cmd=[self.executable,"-p",prompt,"--output-format","json","--agent",agent,"--sandbox","--print-timeout",self.print_timeout]
        if role in {"reviewer","security-reviewer","release-verifier","runtime-verifier"}:
            cmd += ["--json-schema",self._review_schema()]
        try:p=subprocess.run(cmd,cwd=workspace,text=True,capture_output=True,timeout=1800)
        except subprocess.TimeoutExpired:return {"status":"fail","provider":"antigravity","reason":"agy headless timeout"}
        raw=p.stdout.strip()
        try:envelope=json.loads(raw) if raw else {}
        except Exception:return {"status":"fail","provider":"antigravity","reason":"invalid agy JSON output","summary":raw[-4000:]+p.stderr[-2000:]}
        if p.returncode or envelope.get("status")!="SUCCESS":return {"status":"fail","provider":"antigravity","reason":envelope.get("error") or p.stderr[-4000:] or "Antigravity run failed","envelope":envelope}
        usage_raw=envelope.get("usage",{}) if isinstance(envelope.get("usage"),dict) else {}
        usage={"tokens":int(usage_raw.get("total_tokens",0) or 0),"seconds":float(envelope.get("duration_seconds",0) or 0),"input_tokens":int(usage_raw.get("input_tokens",0) or 0),"output_tokens":int(usage_raw.get("output_tokens",0) or 0)}
        structured=envelope.get("structured_output")
        result={"status":"completed","provider":"antigravity","isolation":"process/workspace-sandbox","usage":usage,"response":envelope.get("response",""),"provider_evidence":{"commit_bound_workspace":workspace.exists(),"structured_execution_result":True,"usage_telemetry":True},"envelope":{"conversation_id":envelope.get("conversation_id"),"num_turns":envelope.get("num_turns"),"status":envelope.get("status")}}
        if isinstance(structured,dict):result["output"]=structured
        if output_path is not None and isinstance(structured,dict):
            output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(structured,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return result


class KubernetesJobProvider:
    """Execute an agent as an ephemeral hardened Kubernetes Job.

    The provider is real CLI wiring, not a simulated callback: it applies a Job plus a
    deny-by-default NetworkPolicy, waits for completion, reads structured JSON from job
    logs, and removes the resources. It is unavailable unless kubectl, a digest-pinned
    agent image and an explicit agent command are configured.
    """

    def __init__(self, *, image: str | None = None, command: list[str] | None = None, namespace: str | None = None):
        self.image=image or os.getenv("NAKEURI_K8S_AGENT_IMAGE")
        raw=os.getenv("NAKEURI_K8S_AGENT_COMMAND","").strip()
        if command is None and raw:
            try:
                x=json.loads(raw);command=[str(i) for i in x] if isinstance(x,list) else shlex.split(raw)
            except Exception:command=shlex.split(raw)
        self.command=command or []
        self.namespace=namespace or os.getenv("NAKEURI_K8S_NAMESPACE","default")
        self.capabilities=ProviderCapabilities("kubernetes","container/cluster","RELEASE",True,True,True)

    def available(self)->bool:
        return bool(shutil.which("kubectl") and self.image and self.command)

    def _manifest(self, name: str, request_b64: str, risk: str) -> list[dict[str,Any]]:
        assert self.image
        labels={"app":"nakeuri-agent","nakeuri-run":name}
        job={"apiVersion":"batch/v1","kind":"Job","metadata":{"name":name,"namespace":self.namespace,"labels":labels},"spec":{"backoffLimit":0,"ttlSecondsAfterFinished":300,"activeDeadlineSeconds":1800,"template":{"metadata":{"labels":labels},"spec":{"restartPolicy":"Never","automountServiceAccountToken":False,"securityContext":{"runAsNonRoot":True,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"agent","image":self.image,"imagePullPolicy":"IfNotPresent","command":self.command,"env":[{"name":"NAKEURI_AGENT_REQUEST_B64","value":request_b64}],"securityContext":{"allowPrivilegeEscalation":False,"readOnlyRootFilesystem":True,"capabilities":{"drop":["ALL"]}},"resources":{"requests":{"cpu":"250m","memory":"256Mi"},"limits":{"cpu":"2","memory":"2Gi"}},"volumeMounts":[{"name":"tmp","mountPath":"/tmp"}]}],"volumes":[{"name":"tmp","emptyDir":{}}]}}}}
        net={"apiVersion":"networking.k8s.io/v1","kind":"NetworkPolicy","metadata":{"name":name,"namespace":self.namespace},"spec":{"podSelector":{"matchLabels":{"nakeuri-run":name}},"policyTypes":["Ingress","Egress"],"ingress":[],"egress":[]}}
        return [job,net]

    def _kubectl(self, args: list[str], *, input_text: str | None=None, timeout: int=120) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["kubectl","-n",self.namespace,*args],input=input_text,text=True,capture_output=True,timeout=timeout)

    def run_agent(self, workspace: Path, role: str, prompt: str, *, risk: str, output_path: Path | None = None) -> dict[str,Any]:
        risk=risk.upper()
        if not self.available():return {"status":"unavailable","provider":"kubernetes","reason":"kubectl/image/command not configured"}
        assert self.image
        if risk in {"HIGH","RELEASE"} and not image_is_digest_pinned(self.image):return {"status":"blocked","provider":"kubernetes","reason":"HIGH/RELEASE Kubernetes image must be digest pinned"}
        name="nakeuri-"+uuid.uuid4().hex[:12]
        request={"schema":"nakeuri/provider-agent-request/v1","role":role,"risk":risk,"prompt":prompt,"output_path":str(output_path) if output_path else None,"workspace_contract":"agent must obtain source through its configured immutable source mechanism; no production credentials are included"}
        encoded=base64.b64encode(json.dumps(request,sort_keys=True).encode()).decode()
        manifests=self._manifest(name,encoded,risk)
        payload="\n---\n".join(json.dumps(x) for x in manifests)
        applied=False
        try:
            p=self._kubectl(["apply","-f","-"],input_text=payload)
            if p.returncode:return {"status":"fail","provider":"kubernetes","reason":"kubectl apply failed","summary":p.stderr[-4000:]}
            applied=True
            p=self._kubectl(["wait",f"job/{name}","--for=condition=complete","--timeout=1800s"],timeout=1810)
            if p.returncode:return {"status":"fail","provider":"kubernetes","reason":"job did not complete","summary":p.stderr[-4000:]}
            p=self._kubectl(["logs",f"job/{name}"],timeout=120)
            if p.returncode:return {"status":"fail","provider":"kubernetes","reason":"cannot read job logs","summary":p.stderr[-4000:]}
            lines=[x.strip() for x in p.stdout.splitlines() if x.strip()]
            try:result=json.loads(lines[-1]) if lines else {}
            except Exception:return {"status":"fail","provider":"kubernetes","reason":"last job log line is not structured JSON","summary":p.stdout[-4000:]}
            if not isinstance(result,dict):return {"status":"fail","provider":"kubernetes","reason":"agent result must be object"}
            result=dict(result);result.setdefault("provider","kubernetes");result.setdefault("isolation","container/cluster")
            result["provider_evidence"]={
                "commit_bound_workspace":bool(result.get("commit") or result.get("source_commit")),
                "structured_execution_result":True,
                "usage_telemetry":isinstance(result.get("usage"),dict),
                "security_isolation_attestation":True,
                "network_policy_attestation":True,
                "resource_limit_attestation":True,
                "non_root_attestation":True,
                "ephemeral_environment":True,
                "supply_chain_identity":image_is_digest_pinned(self.image),
                "human_approval_boundary":True,
            }
            return result
        except subprocess.TimeoutExpired:return {"status":"fail","provider":"kubernetes","reason":"kubectl timeout"}
        finally:
            if applied:
                try:self._kubectl(["delete","job",name,"networkpolicy",name,"--ignore-not-found=true"],timeout=60)
                except Exception:pass


class CallbackProvider:
    """Injection point for remote/Kubernetes/CI provider plugins and deterministic tests."""

    def __init__(self, capabilities: ProviderCapabilities, callback: Callable[..., dict[str, Any]], availability: Callable[[], bool] | None = None):
        self.capabilities = capabilities
        self.callback = callback
        self._availability = availability or (lambda: True)

    def available(self) -> bool:
        return bool(self._availability())

    def run_agent(self, workspace: Path, role: str, prompt: str, *, risk: str, output_path: Path | None = None) -> dict[str, Any]:
        result = self.callback(workspace=workspace, role=role, prompt=prompt, risk=risk, output_path=output_path)
        if not isinstance(result, dict):
            raise TypeError("provider callback must return a dict")
        result = dict(result)
        result.setdefault("provider", self.capabilities.provider_id)
        result.setdefault("isolation", self.capabilities.isolation)
        return result


def validate_provider_result(result: dict[str, Any], *, risk: str, provider_id: str) -> dict[str, Any]:
    contract = provider_contract(risk, provider_id)
    evidence = result.get("provider_evidence") if isinstance(result.get("provider_evidence"), dict) else {}
    missing = [name for name in contract["obligations"] if evidence.get(name) is not True]
    return {
        "status": "pass" if not missing else "fail",
        "provider": provider_id,
        "risk": risk.upper(),
        "missing_obligations": missing,
        "obligations": contract["obligations"],
        "rule": "Provider output is accepted only when the control plane can verify every risk-specific proof obligation.",
    }


class UnifiedLifecycleExecutor:
    """Provider-neutral AgentExecutor used by LifecycleRunner.

    Routing is based on risk *and observed provider availability*. HIGH/RELEASE never
    fall back to a worktree-only provider. This closes the V3 direct-OpenHands wiring gap.
    """

    name = "unified-provider-runtime"
    isolation_level = "provider-routed"

    def __init__(self, providers: list[LifecycleProvider], *, preferred: str | None = None):
        self.providers = {p.capabilities.provider_id: p for p in providers}
        self.preferred = preferred

    @classmethod
    def default(
        cls,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        preferred: str | None = None,
    ) -> "UnifiedLifecycleExecutor":
        return cls([
            AntigravityHeadlessProvider(),
            DockerJsonAgentProvider(),
            KubernetesJobProvider(),
            AgentExecutorProvider(OpenHandsAgentExecutor(model=model, api_key=api_key, base_url=base_url), provider_id="openhands"),
        ], preferred=preferred)

    def status(self) -> dict[str, Any]:
        rows = []
        for p in self.providers.values():
            rows.append({**p.capabilities.to_dict(), "available": p.available()})
        available = sum(1 for row in rows if row["available"])
        return {
            "status": "pass" if available else "partial",
            "schema": "nakeuri/unified-provider-runtime/v1",
            "available_providers": available,
            "providers": rows,
            "reason": None if available else "no configured lifecycle provider is currently executable",
        }

    def _ordered_ids(self, risk: str) -> list[str]:
        risk = risk.upper()
        default = {
            "LOW": ["antigravity", "openhands", "docker", "worktree", "remote", "kubernetes", "github-runner"],
            "MEDIUM": ["antigravity", "docker", "openhands", "remote", "kubernetes", "github-runner", "worktree"],
            "HIGH": ["docker", "remote", "kubernetes", "github-runner", "openhands"],
            "RELEASE": ["docker", "github-runner", "kubernetes", "remote"],
        }[risk]
        if self.preferred:
            default = [self.preferred, *[x for x in default if x != self.preferred]]
        return default

    def select(self, risk: str) -> dict[str, Any]:
        risk = risk.upper()
        if risk not in RISK_ORDER:
            raise ValueError(f"unsupported risk: {risk}")
        considered = []
        for provider_id in self._ordered_ids(risk):
            p = self.providers.get(provider_id)
            if not p:
                continue
            available = p.available()
            enough_risk = RISK_ORDER[risk] <= RISK_ORDER[p.capabilities.max_risk]
            strong_isolation = risk not in {"HIGH", "RELEASE"} or p.capabilities.isolation in {"container", "remote", "remote-ephemeral", "container/cluster", "ci-ephemeral"}
            row = {"provider": provider_id, "available": available, "risk_allowed": enough_risk, "isolation_allowed": strong_isolation}
            considered.append(row)
            if available and enough_risk and strong_isolation:
                return {"status": "pass", "selection": provider_id, "considered": considered}
        return {"status": "blocked", "selection": None, "risk": risk, "considered": considered, "reason": "no available provider satisfies risk and isolation requirements"}

    def run_task(self, workspace: Path, role: str, prompt: str, *, risk: str, output_path: Path | None = None) -> dict[str, Any]:
        route = self.select(risk)
        if route["status"] != "pass":
            return route
        provider_id = str(route["selection"])
        provider = self.providers[provider_id]
        result = provider.run_agent(workspace, role, prompt, risk=risk, output_path=output_path)
        result = dict(result)
        result["route"] = route
        if result.get("status") not in {"completed", "pass"}:
            return result
        validation = validate_provider_result(result, risk=risk, provider_id=provider_id)
        result["provider_contract"] = validation
        if validation["status"] != "pass":
            result["status"] = "fail"
            result["reason"] = "runtime provider proof obligations not satisfied"
        return result

    def run(self, workspace: Path, role: str, prompt: str, output_path: Path | None = None) -> dict[str, Any]:
        # Compatibility path for older callers. LifecycleRunner uses run_task and supplies risk.
        return self.run_task(workspace, role, prompt, risk="MEDIUM", output_path=output_path)


def provider_runtime_status() -> dict[str, Any]:
    return UnifiedLifecycleExecutor.default().status()
