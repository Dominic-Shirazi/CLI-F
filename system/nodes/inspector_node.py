import os
import re
from typing import Dict, Any
from system.state import AgentState
from system.agent_runner import run_role, get_prompt_template
from system.git_ops import get_diff_stat


def _extract_reasoning_summary(content: str) -> str:
    """Extract the 4 key structured fields from reasoning.md, capped at ~400 chars."""
    fields = [
        "What I was asked to do",
        "What I actually did",
        "Did I complete the full task?",
        "Any questions?",
    ]
    parts = []
    for field in fields:
        pattern = rf"\*\*{re.escape(field)}\*\*[:\s]*(.*?)(?=\*\*|$)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()[:80]
            parts.append(f"{field}: {value}")
    if parts:
        return " | ".join(parts)
    # Fallback: first 400 chars
    return content[:400].strip()


def build_inspector_node(state: AgentState) -> Dict[str, Any]:
    """Builds the Inspector brief, calls the role, and parses the verdict."""

    current_task = state.get("current_task", "Unknown Task")
    print(f"\n[inspector_node] Starting. task={current_task[:60]}")

    # 1. Verify reasoning.md exists
    reasoning_path = os.path.join("workspace", "gemini_output", "reasoning.md")
    if not os.path.exists(reasoning_path):
        print("[inspector_node] EARLY RETURN: reasoning.md missing")
        return {"gpt_verdict": "INCOMPLETE: reasoning.md was not updated or created"}

    task_path = os.path.join("workspace", "current_task.md")
    if os.path.exists(task_path):
        if os.path.getmtime(reasoning_path) < os.path.getmtime(task_path):
            print("[inspector_node] EARLY RETURN: reasoning.md older than current_task.md")
            return {"gpt_verdict": "INCOMPLETE: reasoning.md is older than current_task.md"}

    # 2. Extract compact summary (protect small context window)
    with open(reasoning_path, "r", encoding="utf-8") as f:
        reasoning_content = f.read()
    reasoning_summary = _extract_reasoning_summary(reasoning_content)
    print(f"[inspector_node] reasoning_summary={reasoning_summary[:100]}")

    # 3. Diff stat only (never full diff body)
    diff_stat = get_diff_stat()
    print(f"[inspector_node] diff_stat=\n{diff_stat}")

    # 4. Load Prompt Template and format
    try:
        template = get_prompt_template("inspector")
        prompt = template.format(
            current_task=current_task,
            reasoning_summary=reasoning_summary,
            diff_stat=diff_stat,
        )
        print(f"[inspector_node] Prompt built OK ({len(prompt)} chars). Calling ollama...")
    except Exception as e:
        print(f"[inspector_node] EARLY RETURN: template format error: {e}")
        return {"gpt_verdict": f"FAIL: Prompt template format error -> {str(e)}"}

    # 5. Call Agent Runner
    try:
        result = run_role("inspector", prompt, state=state)
        output = result.stdout.strip()
        print(f"[inspector_node] ollama stdout={repr(output[:200])}")
        print(f"[inspector_node] ollama stderr={repr(result.stderr[:200])}")
        print(f"[inspector_node] returncode={result.returncode}")
    except Exception as e:
        print(f"[inspector_node] EARLY RETURN: subprocess error: {e}")
        return {"gpt_verdict": f"FAIL: subprocess error -> {str(e)}"}

    # 6. Parse Output Verdict
    valid_prefixes = ["PASS", "INCOMPLETE:", "QUESTION:", "FAIL:", "REVIEW_REQUESTED"]
    verdict = "FAIL: Inspector returned an unparseable response."

    for line in output.splitlines():
        line = line.strip()
        for prefix in valid_prefixes:
            if line.startswith(prefix) or line == prefix:
                verdict = line
                break
        if not verdict.startswith("FAIL: Inspector returned"):
            break

    print(f"[inspector_node] Final verdict: {verdict}")

    # 7. Write to Audit Trail
    audit_dir = os.path.join("audit_trail")
    os.makedirs(audit_dir, exist_ok=True)
    with open(os.path.join(audit_dir, "inspector_verdict.md"), "w", encoding="utf-8") as f:
        f.write(verdict + "\n\nRaw Output:\n" + output)

    return {"gpt_verdict": verdict}
