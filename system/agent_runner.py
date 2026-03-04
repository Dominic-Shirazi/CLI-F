import json
import os
import subprocess
from typing import Optional, Dict, Any
from .state import AgentState

def load_profile(profile_name: str) -> dict:
    """Reads system/profiles/{profile_name}.json and returns the parsed dict."""
    profile_path = os.path.join("system", "profiles", f"{profile_name}.json")
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"Profile '{profile_name}' not found at {profile_path}")
    
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_prompt_template(role: str) -> str:
    """Reads the prompt template path from the profile and returns the raw template string."""
    from dotenv import load_dotenv
    load_dotenv()
    profile_name = os.getenv("ACTIVE_PROFILE", "coder-v2")
    profile = load_profile(profile_name)
    if role not in profile["roles"]:
        raise ValueError(f"Role '{role}' not defined in profile '{profile_name}'")
        
    template_rel_path = profile["roles"][role].get("prompt_template")
    if not template_rel_path:
        raise ValueError(f"No prompt_template defined for role '{role}' in profile '{profile_name}'")
        
    template_path = os.path.join("prompts", template_rel_path)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Prompt template not found at {template_path}")
        
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def _log_event(event: str):
    """Appends an event to brain/progress.txt"""
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + "Z"
    os.makedirs("brain", exist_ok=True)
    with open(os.path.join("brain", "progress.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] | {event}\n")

def trigger_session_refresh(state: AgentState):
    """Forces a session refresh by generating a STATE.md and resetting IDs."""
    # Note: Generating STATE.md via AI is omitted here to prevent infinite recursion
    # In a full flow, you might call a specific "summarizer" prompt here.
    # For now, we update the state to force a cold start on the next run.
    print(f"\n[Agent Runner] Triggering session refresh...")
    state["gemini_session_id"] = None
    state["session_turn_count"] = 0
    _log_event("SESSION_REFRESH | Turn limit or arch switch reached")
    
    os.makedirs("brain", exist_ok=True)
    with open(os.path.join("brain", "STATE.md"), "w", encoding="utf-8") as f:
        f.write(f"# Session State — Step {state.get('step_number', '?')} of {state.get('total_steps', '?')}\n")
        f.write("_Generated automatically during session refresh._\n\n")
        f.write(f"**Reason:** Session turn count reached or arch switch.\n")
        f.write(f"**Last Task:** {state.get('current_task', 'Unknown')}\n")

def run_role(role: str, prompt: str, session_id: Optional[str] = None, resume: bool = False, schema_json: Optional[str] = None, max_turns: int = 10, state: Optional[AgentState] = None) -> subprocess.CompletedProcess:
    """Dispatches the correct CLI subprocess based on the active profile."""
    
    # 1. Profile Lookup
    from dotenv import load_dotenv
    load_dotenv()
    profile_name = os.getenv("ACTIVE_PROFILE", "coder-v2")
    if state and "active_profile" in state:
        profile_name = state["active_profile"]
        
    profile = load_profile(profile_name)
    
    if role not in profile["roles"]:
         raise ValueError(f"Role '{role}' not defined in profile '{profile_name}'")
         
    role_config = profile["roles"][role]
    tool = role_config.get("tool")
    model = role_config.get("model")
    flags = role_config.get("flags", [])
    tools = role_config.get("tools", [])

    # 2. Session Refresh Logic (Writer only)
    if role == "writer" and state is not None:
        max_turns_env = int(os.getenv("SESSION_MAX_TURNS", "20"))
        
        if state.get("session_turn_count", 0) >= max_turns_env:
            trigger_session_refresh(state)
            session_id = None # Force new session
            resume = False
            
    # 3. CLI Dispatch
    step_num = state.get('step_number', '?') if state else '?'
    _log_event(f"STEP {step_num} | {role.upper()}_CALLED | Tool: {tool}")
    
    try:
        env = os.environ.copy()
        
        if tool == "gemini":
            cmd = ["gemini"]
            cmd.extend(flags)
            if resume and session_id:
                 cmd.extend(["-r", session_id])
            cmd.append(prompt)
            print(f"\n[Agent Runner] Dispatching {role} via {tool}...")
            return subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
            
        elif tool == "claude":
            cmd = ["claude", "-p"]
            if tools:
                tools_str = ",".join(tools)
                cmd.extend(["--allowedTools", tools_str])
            cmd.extend(flags)
            if max_turns:
                 cmd.extend(["--max-turns", str(max_turns)])
            if schema_json:
                 cmd.extend(["--json-schema", schema_json])
                 
            if resume and session_id:
                 cmd.extend(["-r", session_id])
            elif session_id:
                 cmd.extend(["--session-id", session_id])
                 
            cmd.append(prompt)
            print(f"\n[Agent Runner] Dispatching {role} via {tool}...")
            return subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
            
        elif tool == "ollama":
             # Ollama "run" expects input on stdin for programmatic queries, or as arguments.
             cmd = ["ollama", "run", model]
             print(f"\n[Agent Runner] Dispatching {role} via {tool}...")
             return subprocess.run(cmd, env=env, input=prompt, capture_output=True, text=True, check=False)
             
        else:
             raise ValueError(f"Unsupported tool '{tool}' configured for role '{role}'")
             
    except subprocess.CalledProcessError as e:
         print(f"[{tool.upper()} Error] {e.stderr}")
         raise
