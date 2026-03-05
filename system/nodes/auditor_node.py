import os
import json
import uuid
from typing import Dict, Any
from system.state import AgentState
from system.agent_runner import run_role, get_prompt_template
from system.git_ops import get_full_diff

def build_auditor_node(state: AgentState) -> Dict[str, Any]:
    """Builds the Reviewer brief, generates a session UUID, and calls Claude."""
    
    current_task = state.get("current_task", "Unknown Task")
    step_number = state.get("step_number", 0)
    claude_session_id = state.get("claude_session_id")

    # 1. Session ID Management
    if not claude_session_id:
        claude_session_id = str(uuid.uuid4())
        resume = False
        max_turns = 10
    else:
        resume = True
        max_turns = 5

    # 2. Gather Context
    reasoning_path = os.path.join("workspace", "gemini_output", "reasoning.md")
    reasoning_summary = ""
    if os.path.exists(reasoning_path):
         with open(reasoning_path, "r", encoding="utf-8") as f:
             reasoning_summary = f.read()
             
    full_diff = get_full_diff()

    # 3. Load Template
    try:
        template = get_prompt_template("reviewer")
        prompt = template.format(
            step_number=step_number,
            current_task=current_task,
            reasoning_summary=reasoning_summary,
            full_diff=full_diff
        )
    except Exception as e:
        return {"claude_audit": {"severity": "CRITICAL", "issue": f"Template format error: {str(e)}", "why_it_matters": "", "suggested_fix": ""}, "claude_session_id": claude_session_id, "ceo_interrupt_flag": True}

    # 4. JSON Schema Definition
    schema = {
        "type": "object",
        "required": ["severity", "issue", "why_it_matters", "suggested_fix"],
        "properties": {
            "severity": { "enum": ["CRITICAL", "MAJOR", "MINOR", "NONE"] },
            "issue": { "type": "string" },
            "why_it_matters": { "type": "string" },
            "suggested_fix": { "type": "string" }
        }
    }
    schema_json = json.dumps(schema)

    # 5. Call Agent Runner
    try:
        result = run_role(
             role="reviewer", 
             prompt=prompt, 
             session_id=claude_session_id, 
             resume=resume,
             schema_json=schema_json,
             max_turns=max_turns,
             state=state
        )
        output = result.stdout.strip()
    except Exception as e:
         return {"claude_audit": {"severity": "CRITICAL", "issue": f"Runner error: {str(e)}", "why_it_matters": "", "suggested_fix": ""}, "claude_session_id": claude_session_id, "ceo_interrupt_flag": True}

    # 6. Parse Output JSON
    # Claude --output-format json wraps the result: {"type":"result","result":"...","session_id":"..."}
    import re as _re
    claude_audit = None
    try:
        if output.startswith("```json"):
            output = output[7:-3].strip()
        parsed_outer = json.loads(output)
        # Unwrap Claude CLI envelope if present
        if "result" in parsed_outer and isinstance(parsed_outer["result"], str):
            inner = parsed_outer["result"].strip()
            if inner.startswith("```json"):
                inner = inner[7:-3].strip()
            claude_audit = json.loads(inner)
        elif "severity" in parsed_outer:
            claude_audit = parsed_outer
    except (json.JSONDecodeError, KeyError):
        pass

    if claude_audit is None:
        # Fallback: regex-extract a JSON block from raw text
        match = _re.search(r'\{[^{}]*"severity"[^{}]*\}', output, _re.DOTALL)
        if match:
            try:
                claude_audit = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    if claude_audit is None:
        claude_audit = {
            "severity": "CRITICAL",
            "issue": "Failed to parse JSON response from Reviewer.",
            "why_it_matters": "The auditor must return valid JSON matching the schema.",
            "suggested_fix": "Check the raw output string and prompt formatting.",
        }

    # 7. Write to Audit Trail
    audit_dir = os.path.join("audit_trail")
    os.makedirs(audit_dir, exist_ok=True)
    with open(os.path.join(audit_dir, "claude_audit_notes.md"), "w", encoding="utf-8") as f:
         f.write(f"# Claude Audit Log (Session: {claude_session_id})\n\n")
         f.write(f"**Severity:** {claude_audit.get('severity')}\n\n")
         f.write(f"**Issue:** {claude_audit.get('issue')}\n\n")
         f.write(f"**Why it Matters:** {claude_audit.get('why_it_matters')}\n\n")
         f.write(f"**Suggested Fix:** {claude_audit.get('suggested_fix')}\n")

    # 8. Set CEO Interrupt Flag
    ceo_interrupt_flag = (claude_audit.get("severity") == "CRITICAL")
    
    return {
        "claude_audit": claude_audit, 
        "claude_session_id": claude_session_id, 
        "ceo_interrupt_flag": ceo_interrupt_flag
    }
