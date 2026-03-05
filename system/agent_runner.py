import json
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
from .state import AgentState

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

def _run_streaming(cmd, label: str, input_text: str = None, encoding: str = "utf-8", shell: bool = False, env=None) -> subprocess.CompletedProcess:
    """Run a subprocess and stream stdout to terminal live while capturing it."""
    kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, shell=shell)
    if input_text is not None:
        kwargs["stdin"] = subprocess.PIPE

    proc = subprocess.Popen(cmd, **kwargs)
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    def read_stdout():
        for raw in proc.stdout:
            stdout_chunks.append(raw)
            try:
                line = raw.decode(encoding, errors="replace").rstrip("\n")
            except Exception:
                line = repr(raw)
            print(f"  \033[2m{label}>\033[0m {line}", flush=True)

    def read_stderr():
        for raw in proc.stderr:
            stderr_chunks.append(raw)

    t1 = threading.Thread(target=read_stdout, daemon=True)
    t2 = threading.Thread(target=read_stderr, daemon=True)
    t1.start(); t2.start()

    if input_text is not None:
        proc.stdin.write(input_text.encode(encoding, errors="replace"))
        proc.stdin.close()

    t1.join(); t2.join()
    proc.wait()

    stdout = b"".join(stdout_chunks).decode(encoding, errors="replace")
    stderr = b"".join(stderr_chunks).decode(encoding, errors="replace")
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout=stdout, stderr=stderr)

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
    total = state.get('total_steps', '?') if state else '?'
    _log_event(f"STEP {step_num} | {role.upper()}_CALLED | Tool: {tool}")
    print(f"\n{'='*55}", flush=True)
    print(f"  STEP {step_num}/{total} — {role.upper()}  [{tool}]  {_ts()}", flush=True)
    print(f"{'='*55}", flush=True)

    try:
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)   # Allow claude CLI to run outside a Claude Code session
        env.pop("CLAUDE_CODE_ENTRYPOINT", None)

        if tool == "gemini":
            prompt_file = os.path.join("workspace", f"prompt_{role}.txt")
            os.makedirs("workspace", exist_ok=True)
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt)

            cmd_str = "gemini"
            if flags:
                cmd_str += " " + " ".join(flags)
            if resume and session_id:
                 cmd_str += f" -r {session_id}"
            cmd_str += f" (Get-Content -Raw '{prompt_file}')"

            print(f"  [{_ts()}] Gemini working... (streaming output below)", flush=True)
            t0 = time.time()
            result = _run_streaming(["powershell.exe", "-NoProfile", "-Command", cmd_str], label="Gemini", env=env)
            print(f"\n  [{_ts()}] Gemini done ({time.time()-t0:.1f}s)", flush=True)
            return result

        elif tool == "claude":
            prompt_file = os.path.join("workspace", f"prompt_{role}.txt")
            os.makedirs("workspace", exist_ok=True)
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt)

            cmd_str = "claude"
            if tools:
                tools_str = ",".join(tools)
                cmd_str += f" --allowedTools {tools_str}"
            if flags:
                cmd_str += " " + " ".join(flags)
            if max_turns:
                cmd_str += f" --max-turns {max_turns}"
            if resume and session_id:
                cmd_str += f" -r {session_id}"

            # Pipe prompt via stdin to avoid Windows 32KB command-line length limit.
            # PowerShell: Get-Content pipes file → claude reads it from stdin via -p -
            ps_cmd = f"Get-Content -Raw '{prompt_file}' | {cmd_str} -p -"
            print(f"  [{_ts()}] Claude working... (streaming output below)", flush=True)
            t0 = time.time()
            result = _run_streaming(["powershell.exe", "-NoProfile", "-Command", ps_cmd], label="Claude", env=env)
            print(f"\n  [{_ts()}] Claude done ({time.time()-t0:.1f}s)", flush=True)
            return result

        elif tool == "ollama":
            cmd = " ".join(["ollama", "run", model])
            print(f"  [{_ts()}] Ollama working... (streaming output below)", flush=True)
            t0 = time.time()
            result = _run_streaming(cmd, label="Ollama", input_text=prompt, encoding="utf-8", shell=True, env=env)
            print(f"\n  [{_ts()}] Ollama done ({time.time()-t0:.1f}s)", flush=True)
            return result

        elif tool == "opencode":
            prompt_file = os.path.join("workspace", f"prompt_{role}.txt")
            os.makedirs("workspace", exist_ok=True)
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt)

            cmd_str = "opencode run --print"
            if model and model != "auto":
                cmd_str += f" --model {model}"
            if flags:
                cmd_str += " " + " ".join(flags)
            cmd_str += f" (Get-Content -Raw '{prompt_file}')"
            
            print(f"\n[Agent Runner] Dispatching {role} via {tool}...")
            return subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd_str], env=env, capture_output=True, text=True, check=False)

        else:
             raise ValueError(f"Unsupported tool '{tool}' configured for role '{role}'")
             
    except subprocess.CalledProcessError as e:
         print(f"[{tool.upper()} Error] {e.stderr}")
         raise
