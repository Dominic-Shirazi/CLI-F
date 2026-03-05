import os
import json
import re
from typing import Dict, Any
from system.state import AgentState
from system.agent_runner import run_role, get_prompt_template
from system.git_ops import get_full_diff

def build_auditor_node(state: AgentState) -> Dict[str, Any]:
    """Calls Claude to audit the diff. Claude reads CLAUDE.md and outputs JSON directly."""

    current_task = state.get("current_task", "Unknown Task")
    step_number = state.get("step_number", 0)

    # 1. Gather Context
    reasoning_path = os.path.join("workspace", "gemini_output", "reasoning.md")
    reasoning_summary = ""
    if os.path.exists(reasoning_path):
        with open(reasoning_path, "r", encoding="utf-8") as f:
            reasoning_summary = f.read()

    full_diff = get_full_diff()

    # 2. Load Template
    try:
        template = get_prompt_template("reviewer")
        prompt = template.format(
            step_number=step_number,
            current_task=current_task,
            reasoning_summary=reasoning_summary,
            full_diff=full_diff,
        )
    except Exception as e:
        return {
            "claude_audit": {"severity": "CRITICAL", "issue": f"Template format error: {str(e)}", "why_it_matters": "", "suggested_fix": ""},
            "ceo_interrupt_flag": True,
        }

    # 3. Call Claude (no --json-schema / --session-id — CLAUDE.md enforces JSON output)
    try:
        result = run_role(role="reviewer", prompt=prompt, max_turns=10, state=state)
        output = result.stdout.strip()
        print(f"\n[auditor_node] Claude returncode={result.returncode}")
        if result.returncode != 0:
            print(f"[auditor_node] stderr: {result.stderr[:300]}")
    except Exception as e:
        return {
            "claude_audit": {"severity": "CRITICAL", "issue": f"Runner error: {str(e)}", "why_it_matters": "", "suggested_fix": ""},
            "ceo_interrupt_flag": True,
        }

    # 4. Parse JSON from Claude's output
    # CLAUDE.md tells Claude to output raw JSON. Try multiple strategies:
    claude_audit = None

    # Strategy A: strip code fence if present, then parse directly
    clean = output
    if "```json" in clean:
        m = re.search(r'```json\s*(.*?)\s*```', clean, re.DOTALL)
        if m:
            clean = m.group(1).strip()
    elif "```" in clean:
        m = re.search(r'```\s*(.*?)\s*```', clean, re.DOTALL)
        if m:
            clean = m.group(1).strip()

    try:
        claude_audit = json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Strategy B: Claude CLI --output-format json envelope {"type":"result","result":"..."}
    if claude_audit is None:
        try:
            outer = json.loads(output)
            if "result" in outer and isinstance(outer["result"], str):
                inner = outer["result"].strip()
                if inner.startswith("```json"):
                    inner = inner[7:inner.rfind("```")].strip()
                claude_audit = json.loads(inner)
            elif "severity" in outer:
                claude_audit = outer
        except (json.JSONDecodeError, KeyError):
            pass

    # Strategy C: regex — find first {...} block containing "severity"
    if claude_audit is None:
        m = re.search(r'\{[^{}]*"severity"[^{}]*\}', output, re.DOTALL)
        if m:
            try:
                claude_audit = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    if claude_audit is None:
        print(f"[auditor_node] RAW OUTPUT (parse failed):\n{output[:800]}")
        claude_audit = {
            "severity": "CRITICAL",
            "issue": "Failed to parse JSON from Claude's response.",
            "why_it_matters": "Auditor output is unparseable.",
            "suggested_fix": "Check raw output above.",
        }

    # 5. Write Audit Trail
    audit_dir = os.path.join("audit_trail")
    os.makedirs(audit_dir, exist_ok=True)
    with open(os.path.join(audit_dir, "claude_audit_notes.md"), "w", encoding="utf-8") as f:
        f.write(f"# Claude Audit — Step {step_number}\n\n")
        f.write(f"**Severity:** {claude_audit.get('severity')}\n\n")
        f.write(f"**Issue:** {claude_audit.get('issue')}\n\n")
        f.write(f"**Why it Matters:** {claude_audit.get('why_it_matters')}\n\n")
        f.write(f"**Suggested Fix:** {claude_audit.get('suggested_fix')}\n")

    ceo_interrupt_flag = claude_audit.get("severity") in ("CRITICAL", "MAJOR")

    return {
        "claude_audit": claude_audit,
        "ceo_interrupt_flag": ceo_interrupt_flag,
    }
