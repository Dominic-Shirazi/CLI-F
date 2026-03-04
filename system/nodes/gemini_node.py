import os
import json
from typing import Dict, Any
from system.state import AgentState
from system.agent_runner import run_role, get_prompt_template

def build_gemini_node(state: AgentState) -> Dict[str, Any]:
    """Manages the Writer CLI session lifecycle."""
    
    current_task = state.get("current_task", "No task assigned")
    last_error = state.get("last_error", "")
    step_number = state.get("step_number", 0)
    session_id = state.get("gemini_session_id")
    session_turn_count = state.get("session_turn_count", 0)
    loop_count = state.get("loop_count", 0)
    new_count = loop_count + 1

    # 1. Cleanup stale reasoning file
    reasoning_path = os.path.join("workspace", "gemini_output", "reasoning.md")
    if os.path.exists(reasoning_path):
        try:
            os.remove(reasoning_path)
        except OSError:
            pass # Ignore deletion errors on stale files

    # 2. Load prompt template
    try:
        template = get_prompt_template("writer")
        prompt = template.format(
            step_number=step_number,
            total_steps=state.get("total_steps", "?"),
            current_task=current_task,
            last_error_block=f"Last Error: {last_error}" if last_error else "None"
        )
    except Exception as e:
        return {"last_error": f"Prompt template error: {str(e)}", "loop_count": new_count}

    # 3. Call Agent Runner
    try:
        resume = bool(session_id)
        # Use run_role. agent_runner handles passing flags, checking refresh thresholds
        result = run_role(
            role="writer", 
            prompt=prompt, 
            session_id=session_id, 
            resume=resume,
            state=state
        )
        
        # 4. Parse Output
        # We expect JSON back from the CLI due to the profile config
        output = result.stdout.strip()
        parsed = {}
        if output.startswith("```json"):
            output = output[7:-3].strip()
        
        try:
            parsed = json.loads(output)
            reasoning = parsed.get("reasoning", "")
        except json.JSONDecodeError:
            reasoning = output # Fallback if CLI didn't respect output-format JSON

        # 5. Verify Reasoning Exists (Written directly by Gemini CLI)
            
        # 6. Verify Reasoning Exists
        if not os.path.exists(reasoning_path) or os.path.getsize(reasoning_path) == 0:
            return {"last_error": "reasoning.md not written or empty", "loop_count": new_count}

        return {
            "gemini_session_id": "latest", 
            "loop_count": new_count, 
            "session_turn_count": session_turn_count + 1,
            "last_error": None # Clear previous errors
        }

    except Exception as e:
        return {"last_error": f"Agent Runner error: {str(e)}", "loop_count": new_count}
