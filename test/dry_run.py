import os
import sys
import shutil
import subprocess

# Ensure the root directory is in sys.path
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch
from typing import Dict, Any

# We must import these after patching or use the full path in patch()
# but let's mock the classes directly inside the run function.

from system.graph import app
from system.state import AgentState

# Shared test state to track which step we are on during the stream
test_state = {
    "current_step": 1,
    "fail_on_step": None,    # Scenario 2: Fail on this step
    "critical_on_step": None # Scenario 3: Interrupt on this step
}

def mock_subprocess_run(cmd, **kwargs):
    """Mocks CLI calls for gemini, claude, and ollama."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""

    # 1. Gemini Builder CLI
    if cmd[0] == "gemini":
        result.stdout = f"<h1>Step {test_state['current_step']} Code</h1>\n"
        # Side-effect: simulate Gemini writing the changelog
        os.makedirs(os.path.join("workspace", "gemini_output"), exist_ok=True)
        with open(os.path.join("workspace", "gemini_output", "changelog.md"), "w", encoding="utf-8") as f:
            f.write(f"## Changelog — Step {test_state['current_step']}\n**What I built:** Feature {test_state['current_step']}\n")

    # 2. GPT-OSS Inspector (Ollama)
    elif cmd[0] == "ollama":
        if test_state["fail_on_step"] == test_state["current_step"]:
            # One-time fail: clear it so next retry passes
            test_state["fail_on_step"] = None
            result.stdout = "FAIL: Logic error in the generated code."
        else:
            result.stdout = "PASS"

    # 3. Claude Auditor CLI
    elif cmd[0] == "claude":
        if test_state["critical_on_step"] == test_state["current_step"]:
            result.stdout = "## Audit\n**Severity:** CRITICAL\n**Issue:** Security flaw.\n**Suggested fix:** Stop!"
        else:
            result.stdout = "## Audit\n**Severity:** NONE\n**Issue:** Looks good."
        
    return result

def run_test_scenario(scenario_name, fail_step=None, critical_step=None, use_api=False):
    print(f"\n{'='*50}\nStarting {scenario_name}\n{'='*50}")
    
    test_state["current_step"] = 1
    test_state["fail_on_step"] = fail_step
    test_state["critical_on_step"] = critical_step

    initial_state = {
        "step_number": 1,
        "current_task": "Executing step 1 from MASTER_PLAN.md",
        "loop_count": 0,
        "ceo_interrupt_flag": False,
        "changelog_history": [],
    }

    if use_api:
        os.environ["USE_API_MODE"] = "true"
        os.environ["ANTHROPIC_API_KEY"] = "sk-fake-key"
        os.environ["GEMINI_API_KEY"] = "fake-genai-key"
    else:
        os.environ["USE_API_MODE"] = "false"

    config = {"configurable": {"thread_id": f"dry_run_{scenario_name.replace(' ', '_')}"}}
    
    # Track results
    final_state = None

    # Mocks for SDKs
    mock_anthropic = MagicMock()
    mock_response_anthropic = MagicMock()
    content_mock = MagicMock()
    content_mock.text = "## Audit — Step API\n**Severity:** NONE\n**Issue:** All good.\n**Why it matters:** Testing SDK.\n**Suggested fix:** None."
    mock_response_anthropic.content = [content_mock]
    # Path: client.beta.prompt_caching.messages.create
    mock_anthropic.return_value.beta.prompt_caching.messages.create.return_value = mock_response_anthropic
    
    # Mock for Gemini SDK
    mock_genai = MagicMock()
    mock_response_gemini = MagicMock()
    # Path: response.text
    mock_response_gemini.text = "<h1>Hello from SDK</h1>\n"
    # Path: genai.GenerativeModel.generate_content
    mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response_gemini

    def side_effect_gemini_changelog(*args, **kwargs):
        os.makedirs(os.path.join("workspace", "gemini_output"), exist_ok=True)
        with open(os.path.join("workspace", "gemini_output", "changelog.md"), "w", encoding="utf-8") as f:
            f.write("## Changelog — Step API\n**What I built:** SDK Code.\n**Files modified:** index.html\n")
        return mock_response_gemini

    mock_genai.GenerativeModel.return_value.generate_content.side_effect = side_effect_gemini_changelog

    # Patch everything
    with patch("subprocess.run", side_effect=mock_subprocess_run), \
         patch("anthropic.Anthropic", mock_anthropic), \
         patch("google.generativeai.configure", mock_genai.configure), \
         patch("google.generativeai.GenerativeModel", mock_genai.GenerativeModel):
        
        # We loop over the generator
        generator = app.stream(initial_state, config=config)
        
        for event in generator:
            for node_name, state_update in event.items():
                # Read state before this node's updates
                current_state = app.get_state(config).values
                
                # Merge updates for logging accuracy if they are a mapping
                if isinstance(state_update, dict):
                    display_state = {**current_state, **state_update}
                else:
                    # It's likely an interrupt or other non-node event
                    display_state = current_state
                
                loop = display_state.get("loop_count", 0)
                step = display_state.get("step_number", 1)
                ceo = display_state.get("ceo_interrupt_flag", False)
                
                print(f"--- Completed: {node_name} --- | Step: {step} | Loop: {loop} | CEO: {ceo}")
                
                if isinstance(state_update, dict) and node_name == "inspector_node" and state_update.get("gpt_verdict", "").startswith("FAIL"):
                    print(f">>> SIMULATED FAIL on Step {test_state['current_step']}: Routing back to Gemini...")
                
                if isinstance(state_update, dict) and node_name == "auditor_node" and state_update.get("ceo_interrupt_flag"):
                    print(f"\n>>> SIMULATED CRITICAL on Step {test_state['current_step']}: Execution paused for CEO interrupt. Graph successfully halted!")
                
                if node_name == "step_approved":
                    test_state["current_step"] += 1
                
                final_state = display_state

    # Reporter check (Simulator)
    if final_state and final_state.get("current_task") == "DONE":
        print("\nFINAL STATUS UPDATE:")
        print("[Status Update reads valid (emoji suppressed due to terminal encoding)]")

def run_dry_run():
    # 0. Cleanup previous workspace/audit/status
    for d in ["workspace", "audit_trail", "status", "system/checkpoints"]:
        if os.path.exists(d):
            shutil.rmtree(d)
    os.makedirs("status", exist_ok=True)
    os.makedirs("brain", exist_ok=True)
    os.makedirs("workspace", exist_ok=True)
    os.makedirs("system/checkpoints", exist_ok=True)

    # 1. Create a dummy test plan
    with open(os.path.join("test", "dry_run_plan.md"), "w", encoding="utf-8") as f:
        f.write("# Dry Run Plan\n- [ ] Step 1\n- [ ] Step 2\n- [ ] Step 3\n")
    
    # 2. Copy the fake plan to MASTER_PLAN.md
    shutil.copy(os.path.join("test", "dry_run_plan.md"), os.path.join("brain", "MASTER_PLAN.md"))

    # Scenario 1: Happy Path (CLI)
    run_test_scenario("Scenario 1: Happy Path", use_api=False)
    
    # Scenario 2: Inspector FAIL Loop (CLI)
    run_test_scenario("Scenario 2: Inspector FAIL Loop", fail_step=2, use_api=False)
    
    # Scenario 3: Auditor CRITICAL Interrupt (CLI)
    run_test_scenario("Scenario 3: Auditor CRITICAL Interrupt", critical_step=3, use_api=False)

    # Scenario 4: Happy Path (API SDK Mode)
    run_test_scenario("Scenario 4: API Mode Happy Path", use_api=True)

if __name__ == "__main__":
    # Ensure environment is clean
    if "USE_API_MODE" in os.environ:
        del os.environ["USE_API_MODE"]

    run_dry_run()
