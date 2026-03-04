import os
from typing import Dict, Any
from system.state import AgentState
from system.agent_runner import run_role, get_prompt_template
from system.git_ops import get_diff_stat

def build_inspector_node(state: AgentState) -> Dict[str, Any]:
    """Builds the Inspector brief, calls the role, and parses the verdict."""
    
    current_task = state.get("current_task", "Unknown Task")
    step_number = state.get("step_number", 0)
    total_steps = state.get("total_steps", 0)

    # 1. Verification of Reasoning (Zero-token programmatic check)
    reasoning_path = os.path.join("workspace", "gemini_output", "reasoning.md")
    if not os.path.exists(reasoning_path):
        return {"gpt_verdict": "INCOMPLETE: reasoning.md was not updated or created"}
        
    task_path = os.path.join("workspace", "current_task.md")
    if os.path.exists(task_path):
        if os.path.getmtime(reasoning_path) < os.path.getmtime(task_path):
             return {"gpt_verdict": "INCOMPLETE: reasoning.md is older than current_task.md"}

    # 2. Gather Brief Context
    with open(reasoning_path, "r", encoding="utf-8") as f:
        reasoning_content = f.read()
        
    diff_stat = get_diff_stat()
    
    env_rules_path = os.path.join("brain", "ENVIRONMENT_RULES.md")
    env_rules = ""
    if os.path.exists(env_rules_path):
        with open(env_rules_path, "r", encoding="utf-8") as f:
            env_rules = f.read()

    # 3. Load Prompt Template and format
    try:
        template = get_prompt_template("inspector")
        prompt = template.format(
            step_number=step_number,
            total_steps=total_steps,
            current_task=current_task,
            reasoning_content=reasoning_content,
            diff_stat=diff_stat,
            environment_rules=env_rules
        )
    except Exception as e:
        return {"gpt_verdict": f"FAIL: Prompt template format error -> {str(e)}"}

    # 4. Call Agent Runner
    try:
        result = run_role("inspector", prompt, state=state)
        output = result.stdout.strip()
    except Exception as e:
        return {"gpt_verdict": f"FAIL: subprocess error -> {str(e)}"}

    # 5. Parse Output Verdict
    valid_prefixes = ["PASS", "INCOMPLETE:", "QUESTION:", "FAIL:", "REVIEW_REQUESTED"]
    verdict = "FAIL: Inspector returned an unparseable response."
    
    for line in output.splitlines():
        line = line.strip()
        for prefix in valid_prefixes:
            if line.startswith(prefix) or line == prefix:
                verdict = line
                break
        if not verdict.startswith("FAIL: Inspector returned"):
             break # Found a valid verdict

    # 6. Write to Audit Trail
    audit_dir = os.path.join("audit_trail")
    os.makedirs(audit_dir, exist_ok=True)
    with open(os.path.join(audit_dir, "inspector_verdict.md"), "w", encoding="utf-8") as f:
        f.write(verdict + "\n\nRaw Output:\n" + output)

    return {"gpt_verdict": verdict}
