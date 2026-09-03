from __future__ import annotations

import importlib.util
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class AgentExecutor(Protocol):
    """Role-oriented agent execution contract used by the lifecycle runner."""

    name: str
    isolation_level: str

    def run(self, workspace: Path, role: str, prompt: str, output_path: Path | None = None) -> dict[str, Any]: ...


@dataclass
class ScriptedAgentExecutor:
    """Deterministic executor for tests and controlled automation.

    A callback is deliberately required: this executor must never masquerade as an AI agent.
    """

    callback: Any
    name: str = "scripted"
    isolation_level: str = "test"

    def run(self, workspace: Path, role: str, prompt: str, output_path: Path | None = None) -> dict[str, Any]:
        result = self.callback(workspace, role, prompt, output_path)
        if not isinstance(result, dict):
            raise TypeError("agent callback must return a dict")
        return result


@dataclass
class OpenHandsAgentExecutor:
    """Optional OpenHands Software Agent SDK adapter.

    It follows the current public SDK quick-start surface (LLM, Agent, Conversation,
    Tool + Terminal/FileEditor/TaskTracker). Local mode is worktree isolation only;
    HIGH/RELEASE lifecycle execution must not treat it as a container sandbox.
    """

    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    name: str = "openhands-sdk"
    isolation_level: str = "worktree"

    @staticmethod
    def available() -> bool:
        try:
            return importlib.util.find_spec("openhands.sdk") is not None and importlib.util.find_spec("openhands.tools") is not None
        except (ModuleNotFoundError, ValueError):
            return False

    def _config(self) -> tuple[str, str | None, str | None]:
        model = self.model or os.getenv("LLM_MODEL")
        if not model:
            raise RuntimeError("OpenHands executor requires LLM_MODEL or model=")
        return model, self.api_key or os.getenv("LLM_API_KEY"), self.base_url or os.getenv("LLM_BASE_URL")

    def run(self, workspace: Path, role: str, prompt: str, output_path: Path | None = None) -> dict[str, Any]:
        if not self.available():
            return {"status": "unavailable", "executor": self.name, "reason": "openhands-sdk/openhands-tools are not installed"}

        # Imports intentionally stay inside run so Foundry remains usable without the optional runtime.
        from openhands.sdk import LLM, Agent, Conversation, Tool  # type: ignore
        from openhands.tools.file_editor import FileEditorTool  # type: ignore
        from openhands.tools.task_tracker import TaskTrackerTool  # type: ignore
        from openhands.tools.terminal import TerminalTool  # type: ignore

        model, api_key, base_url = self._config()
        llm = LLM(model=model, api_key=api_key, base_url=base_url)
        agent = Agent(
            llm=llm,
            tools=[Tool(name=TerminalTool.name), Tool(name=FileEditorTool.name), Tool(name=TaskTrackerTool.name)],
        )
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        if output_path is not None:
            output_path = output_path.resolve(strict=False)
            try:
                output_path.relative_to(workspace)
            except ValueError:
                return {"status": "fail", "executor": self.name, "reason": "output path escapes workspace"}
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                output_path.unlink()
            except FileNotFoundError:
                pass
            prompt = (
                prompt.rstrip()
                + "\n\nOUTPUT CONTRACT:\n"
                + f"Write your final machine-readable JSON result to exactly: {output_path}\n"
                + "Do not claim completion unless that file has been written."
            )

        conversation = Conversation(agent=agent, workspace=str(workspace))
        started=time.monotonic()
        conversation.send_message(prompt)
        conversation.run()
        elapsed=time.monotonic()-started
        metrics=None
        try: metrics=conversation.conversation_stats.get_combined_metrics()
        except Exception:
            try: metrics=conversation.state.stats.get_combined_metrics()
            except Exception: metrics=None
        cost=float(getattr(metrics,"accumulated_cost",0.0) or 0.0) if metrics is not None else 0.0
        token_usage=getattr(metrics,"accumulated_token_usage",None) if metrics is not None else None
        tokens=0
        if token_usage is not None:
            for field in ("prompt_tokens","completion_tokens","reasoning_tokens"):
                try: tokens += int(getattr(token_usage,field,0) or 0)
                except Exception: pass

        out: dict[str, Any] = {
            "status": "completed",
            "executor": self.name,
            "role": role,
            "isolation_level": self.isolation_level,
            "usage": {"cost_usd": cost, "tokens": tokens, "seconds": round(elapsed, 3)},
        }
        if output_path is not None:
            if not output_path.exists():
                return {**out, "status": "fail", "reason": "agent did not produce required output artifact"}
            try:
                payload = json.loads(output_path.read_text(encoding="utf-8"))
            except Exception as exc:
                return {**out, "status": "fail", "reason": f"invalid agent output JSON: {exc}"}
            out["output"] = payload
        return out


def runtime_status() -> dict[str, Any]:
    return {
        "openhands_sdk": OpenHandsAgentExecutor.available(),
        "install_hint": "pip install -e .[openhands] on Python >=3.12 for the optional OpenHands executor",
        "python_requirement_note": "OpenHands SDK current releases require Python >=3.12; Foundry core remains usable without it.",
        "local_isolation": "worktree",
        "high_release_rule": "HIGH/RELEASE should use a container/remote executor or require explicit human exception; local OpenHands execution is not a sandbox.",
    }
