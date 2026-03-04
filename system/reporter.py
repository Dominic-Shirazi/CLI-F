import os
from system.state import AgentState
from system.git_ops import get_diff_stat
from system.agent_runner import _log_event

def build_reporter(state: AgentState) -> None:
    """
    Builds the STATUS_UPDATE.md file at the end of a successful step, 
    compiling the git diff stats, inspector verdicts, and Claude severities.
    """
    step_num = state.get("step_number", 0)
    task_name = state.get("current_task", "Completed Task")
    
    # Extract git diff stats
    try:
        diff_stat = get_diff_stat()
        if not diff_stat:
            diff_stat = "No tracked file changes."
    except Exception as e:
        diff_stat = f"Error retrieving git diff: {e}"

    # Extract verdicts and loops
    inspector_verdict = state.get("gpt_verdict", "N/A").strip()
    claude_audit = state.get("claude_audit", {})
    claude_severity = claude_audit.get("severity", "NONE")
    claude_note = claude_audit.get("issue", "No issues flagged.")
    loop_count = state.get("loop_count", 0)

    # Determine action required
    action_required = "NO"
    if state.get("ceo_interrupt", False) or claude_severity == "CRITICAL":
        action_required = "YES — Critical issue or QUESTION raised. Review needed."

    # Build markdown
    report_content = f"""## Sprint Summary — Step {step_num}
**Task:** {task_name}
**Result:** {'APPROVED ✅' if claude_severity == 'NONE' else 'PENDING YOUR INPUT ⚠️'}

**Files changed this step:**
```text
{diff_stat}
```

**Metrics:**
- **Inspector verdict:** {inspector_verdict}
- **Claude severity:** {claude_severity}
- **Gemini loops this step:** {loop_count}

**Claude's note:**
> {claude_note}

**Action required:** {action_required}
"""

    status_path = os.path.join("status", "STATUS_UPDATE.md")
    
    try:
        os.makedirs(os.path.dirname(status_path), exist_ok=True)
        with open(status_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        _log_event("REPORTER_WRITTEN | STATUS_UPDATE.md generated")
    except Exception as e:
        print(f"Failed to write STATUS_UPDATE.md: {e}")
