"""Load an Erza run directory into a normalised trajectory object.

An Erza run directory (`trajectories/<task>/<model>/<arm>/run_N/`) holds
`trajectory/llm_trajectory.jsonl`: one JSON object per API call, each carrying
the *entire* message history sent on that call plus the response. The last line
therefore already contains the full conversation; the final assistant turn lives
in that line's response body.

This module turns that into three views, which are what both verifier channels
read:

  * `turns`      - ordered [{role, type, text}] over the whole conversation
  * `commands`   - every shell command / file write the agent actually issued
  * `transcript` - a flat readable rendering, for the human reviewer

Nothing here interprets the task. Task-specific claims live in `rubrics.json`
and are checked by `test_output.py` (deterministic) or the human reviewer
(human).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _text_of(block: dict) -> str:
    """Best-effort text for one content block, whatever shape it arrived in."""
    t = block.get("type")
    if t == "text":
        return block.get("text", "")
    # OpenAI Responses content blocks (codex-acp). The Anthropic shape above
    # calls this "text"; the Responses shape splits it by direction.
    if t in ("input_text", "output_text"):
        return block.get("text", "") or ""
    if t == "tool_use":
        return json.dumps(block.get("input", {}), ensure_ascii=False)
    if t == "tool_result":
        content = block.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        return ""
    if t == "thinking":
        return block.get("thinking", "") or ""
    return ""


@dataclass
class Turn:
    role: str
    type: str
    text: str
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)


@dataclass
class Trajectory:
    run_dir: str
    turns: list[Turn]
    score: float | None
    pass_at_1: int | None

    # ---------------- derived views ----------------

    @property
    def commands(self) -> list[str]:
        """Every shell command string the agent issued, in order."""
        out = []
        for t in self.turns:
            if t.type != "tool_use":
                continue
            inp = t.tool_input
            for key in ("command", "cmd", "script"):
                v = inp.get(key)
                if isinstance(v, str):
                    out.append(v)
        return out

    @property
    def file_writes(self) -> list[tuple[str, str]]:
        """(path, content) for every file the agent wrote via a write/edit tool."""
        out = []
        for t in self.turns:
            if t.type != "tool_use":
                continue
            inp = t.tool_input
            path = inp.get("file_path") or inp.get("path") or ""
            content = (
                inp.get("content")
                or inp.get("file_text")
                or inp.get("new_string")
                or ""
            )
            if path and content:
                out.append((str(path), str(content)))
            elif t.tool_name == "apply_patch":
                out.extend(_apply_patch_files(t.text))
        return out


    @property
    def tool_surface(self) -> str:
        """Every tool invocation's input, serialised.

        `agent_code` covers writes and shell commands, but a run that opens a file
        with a read-only tool leaves NO trace in either: a Read call carries a
        `file_path` and no `content`, so `file_writes` skips it and `commands`
        never sees it. A detector asking "did the run open this file?" that greps
        only `agent_code` therefore reports a false negative on every run that
        used the read tool - which is most of them.

        This view is deliberately a superset and interprets nothing.
        """
        import json as _json
        parts = []
        for t in self.turns:
            if t.type == "tool_use":
                parts.append(t.tool_name or "")
                parts.append(_json.dumps(t.tool_input, ensure_ascii=False))
        return "\n".join(parts)

    @property
    def agent_code(self) -> str:
        """All source the agent authored: file writes plus heredoc'd commands.

        This is what the deterministic channel greps. It is deliberately a
        superset - a convention that appears in a discarded draft still counts
        as the agent having considered it.
        """
        parts = [c for _p, c in self.file_writes]
        parts += self.commands
        return "\n\n".join(parts)

    @property
    def agent_prose(self) -> str:
        """Everything the agent said or thought, excluding tool plumbing."""
        return "\n\n".join(
            t.text for t in self.turns
            if t.role == "assistant" and t.type in ("text", "thinking")
        )

    @property
    def transcript(self) -> str:
        """Flat readable rendering for the human reviewer."""
        lines = []
        for i, t in enumerate(self.turns):
            head = f"--- [{i}] {t.role}/{t.type}"
            if t.tool_name:
                head += f" ({t.tool_name})"
            lines.append(head + " ---")
            lines.append(t.text)
        return "\n".join(lines)


def _read_score(run_dir: str, name: str):
    p = os.path.join(run_dir, "verifier", name)
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return None


def _acp_as_llm_record(acp_path: str) -> dict:
    """Build one llm_trajectory-shaped record from an ACP trajectory.

    Fallback for a run that carries no `llm_trajectory.jsonl`, where only the
    ACP event stream survives. ACP carries what the agent DID and SAID; it does
    not carry what it SAW: `tool_call.content` is empty in such a recording,
    because tool output was never captured. An ACP-derived transcript is therefore one-sided by
    construction, and a criterion about the agent reacting to tool output is
    strictly harder to satisfy from it than from the LLM channel. That
    asymmetry is a property of the RECORDING, not of the run.

    Mapping (order preserved exactly as recorded):
      user_message  -> user/text
      agent_message -> assistant/text
      agent_thought -> assistant/thinking
      tool_call     -> assistant/tool_use, tool named for its ACP `kind`
                       kind == "execute": the shell command is the `title`, so it
                       lands under `input["command"]` and reaches `commands` and
                       `agent_code` exactly as an llm tool_use would.
                       Any other kind (read/search/edit/think/other) carries only
                       a human-readable label ("Editing files"), never a command
                       and never file content, so it goes to `input["description"]`
                       - outside `commands` and outside `file_writes`, which would
                       otherwise ingest prose as if it were source the agent wrote.
      agent_timeout -> system/text, so a truncated run reads as truncated rather
                       than as an agent that simply stopped.

    Emitting no tool_result blocks is deliberate: fabricating empty ones would
    assert the agent saw an empty result, which is a stronger and false claim
    than recording nothing.
    """
    messages = []
    with open(acp_path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except ValueError:
                continue
            kind = rec.get("type")
            if kind == "user_message":
                messages.append({"role": "user", "content": [
                    {"type": "text", "text": rec.get("text", "") or ""}]})
            elif kind == "agent_message":
                messages.append({"role": "assistant", "content": [
                    {"type": "text", "text": rec.get("text", "") or ""}]})
            elif kind == "agent_thought":
                messages.append({"role": "assistant", "content": [
                    {"type": "thinking", "thinking": rec.get("text", "") or ""}]})
            elif kind == "tool_call":
                title = rec.get("title", "") or ""
                tool_kind = rec.get("kind", "") or "other"
                key = "command" if tool_kind == "execute" else "description"
                messages.append({"role": "assistant", "content": [
                    {"type": "tool_use", "name": tool_kind, "input": {key: title}}]})
            elif kind == "agent_timeout":
                messages.append({"role": "system", "content": [
                    {"type": "text",
                     "text": "[agent_timeout reason=%s timeout_sec=%s complete=%s]" % (
                         rec.get("reason"), rec.get("timeout_sec"),
                         rec.get("terminal_trajectory_complete"))}]})
    # response body left empty: the last agent_message is already the final turn
    return {"request": {"body": {"messages": messages}}, "response": {"body": {}}}


def _apply_patch_files(patch: str) -> list[tuple[str, str]]:
    """(path, content) pairs from an apply_patch payload.

    `Add File` bodies are the file verbatim; `Update File` bodies are the added
    lines of each hunk - which is what the deterministic channel greps for.
    """
    out: list[tuple[str, str]] = []
    path, lines = None, []
    for ln in patch.splitlines():
        if ln.startswith("*** Add File: ") or ln.startswith("*** Update File: "):
            if path is not None and lines:
                out.append((path, "\n".join(lines)))
            path, lines = ln.split(": ", 1)[1].strip(), []
        elif ln.startswith("*** "):
            if path is not None and lines:
                out.append((path, "\n".join(lines)))
            path, lines = None, []
        elif path is not None and ln.startswith("+"):
            lines.append(ln[1:])
    if path is not None and lines:
        out.append((path, "\n".join(lines)))
    return out


_RESPONSES_ITEM_TYPES = frozenset({
    "function_call", "function_call_output",
    "custom_tool_call", "custom_tool_call_output",
    "reasoning", "web_search_call",
})


def _responses_item_turns(item: dict) -> list["Turn"]:
    """Turns for one OpenAI Responses API item.

    Mapped onto the vocabulary the Anthropic shape already produces, so a reviewer
    reads both arms through one transcript format: a model-issued call is
    `tool_use` on the assistant, its result is `tool_result` on the user, and a
    reasoning item is `thinking`. Only the plaintext `summary` of a reasoning
    item is carried -- `encrypted_content` is opaque by construction.
    """
    t = item.get("type")
    if t == "function_call":
        raw = item.get("arguments", "") or ""
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        return [Turn("assistant", "tool_use", raw,
                     tool_name=item.get("name", "") or "",
                     tool_input=parsed if isinstance(parsed, dict)
                                else {"arguments": raw})]
    if t == "custom_tool_call":
        return [Turn("assistant", "tool_use", str(item.get("input", "") or ""),
                     tool_name=item.get("name", "") or "",
                     tool_input={"input": item.get("input", "") or ""})]
    if t == "web_search_call":
        return [Turn("assistant", "tool_use",
                     json.dumps(item.get("action", {}), ensure_ascii=False),
                     tool_name="web_search", tool_input=item.get("action", {}) or {})]
    if t in ("function_call_output", "custom_tool_call_output"):
        out = item.get("output")
        if not isinstance(out, str):
            out = json.dumps(out, ensure_ascii=False) if out is not None else ""
        return [Turn("user", "tool_result", out)]
    if t == "reasoning":
        parts = [p.get("text", "") for p in (item.get("summary") or [])
                 if isinstance(p, dict)]
        text = "\n".join(p for p in parts if p)
        return [Turn("assistant", "thinking", text)] if text else []
    return []


def load(run_dir: str) -> Trajectory:
    path = os.path.join(run_dir, "trajectory", "llm_trajectory.jsonl")
    lines = []
    if os.path.exists(path):
        with open(path) as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]

    if lines:
        last = json.loads(lines[-1])
    else:
        # ACP fallback: no llm_trajectory was recorded for this run. See
        # `_acp_as_llm_record` for the mapping and for what ACP cannot carry.
        acp_path = os.path.join(run_dir, "trajectory", "acp_trajectory.jsonl")
        if not os.path.exists(acp_path):
            raise ValueError(f"empty trajectory: {path}")
        last = _acp_as_llm_record(acp_path)
        if not last["request"]["body"]["messages"]:
            raise ValueError(f"empty trajectory: {acp_path}")

    messages = last["request"]["body"]["messages"]

    turns: list[Turn] = []
    for m in messages:
        # OpenAI Responses API items (codex-acp) are not role/content messages:
        # they are typed items whose payload lives in `arguments` / `output` /
        # `summary`. Without this branch every tool call, tool result and
        # reasoning step of a gpt run is dropped and the transcript reads empty.
        item = m.get("type")
        if item in _RESPONSES_ITEM_TYPES:
            turns.extend(_responses_item_turns(m))
            continue
        role = m.get("role", "?")
        content = m.get("content")
        if isinstance(content, str):
            turns.append(Turn(role, "text", content))
            continue
        for block in content or []:
            if not isinstance(block, dict):
                continue
            turns.append(
                Turn(
                    role=role,
                    type=block.get("type", "?"),
                    text=_text_of(block),
                    tool_name=block.get("name", ""),
                    tool_input=block.get("input", {}) or {},
                )
            )

    # final assistant turn: it is the response of the last recorded call, and so
    # never appears in any request's message list
    body = last.get("response", {}).get("body", {}) or {}
    final = ""
    for choice in body.get("choices", []) or []:
        c = (choice.get("message") or {}).get("content")
        if isinstance(c, str):
            final += c
    if not final:  # native anthropic response shape
        for block in body.get("content", []) or []:
            if isinstance(block, dict):
                final += _text_of(block)
    if final:
        turns.append(Turn("assistant", "text", final))

    score = _read_score(run_dir, "score.md")
    # pass@1 is derived from the structured record: pass_at_1.txt no longer ships,
    # and process.json is the authoritative per-case report.
    p1 = None
    try:
        with open(os.path.join(run_dir, "verifier", "process.json")) as f:
            oc = json.load(f).get("outcome") or {}
        if oc.get("cases_total"):
            p1 = int(oc.get("cases_passed") == oc.get("cases_total"))
    except (OSError, ValueError):
        p1 = None
    return Trajectory(
        run_dir=run_dir,
        turns=turns,
        score=float(score) if score else None,
        pass_at_1=p1,
    )
