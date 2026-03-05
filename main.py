"""
EndToEndDev — Main entry point.

Loads MASTER_PLAN.md, initialises AgentState, then runs the LangGraph loop.
When the graph hits `interrupt_before=["ceo_review"]`, this script:
  1. Reads the paused state
  2. Formats an alert message
  3. Sends it via Telegram (or falls back to terminal input)
  4. Injects the CEO's reply and resumes the graph

Usage:
    python main.py
    python main.py --profile power-inspector   (override ACTIVE_PROFILE)
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from system.graph import create_graph
from system.state import AgentState
from system import ceo_comms


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_master_plan() -> list[str]:
    """Parse brain/MASTER_PLAN.md and return the list of unchecked task strings."""
    path = os.path.join("brain", "MASTER_PLAN.md")
    if not os.path.exists(path):
        print(f"[Main] ERROR: {path} not found. Create it before running.")
        sys.exit(1)

    tasks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                tasks.append(stripped[5:].strip())
            elif stripped.startswith("- []"):
                tasks.append(stripped[4:].strip())

    return tasks


def format_ceo_alert(state: dict) -> str:
    """Build the Telegram / terminal message for a CEO review interrupt."""
    step = state.get("step_number", "?")
    total = state.get("total_steps", "?")
    task = state.get("current_task", "Unknown task")
    verdict = state.get("gpt_verdict") or ""
    audit = state.get("claude_audit") or {}
    severity = audit.get("severity", "")
    issue = audit.get("issue", "")
    suggested_fix = audit.get("suggested_fix", "")
    loop_count = state.get("loop_count", 0)

    lines = [
        f"🚨 *EndToEndDev — CEO Review Required*",
        f"*Step {step}/{total}:* {task}",
        f"",
    ]

    if verdict.startswith("QUESTION:"):
        lines += [
            f"*Gemini has a question:*",
            f"`{verdict}`",
        ]
    elif severity in ("CRITICAL", "MAJOR"):
        lines += [
            f"*Claude Audit: {severity}*",
            f"*Issue:* {issue}",
            f"*Suggested fix:* {suggested_fix}",
        ]
    elif loop_count >= 3:
        lines += [
            f"*Loop guard triggered* — Gemini looped {loop_count}× without resolving.",
            f"*Last error:* {state.get('last_error', 'None')}",
        ]
    else:
        lines.append(f"*Reason:* Unknown interrupt. Last error: {state.get('last_error', 'None')}")

    lines += [
        f"",
        f"Reply with instructions, or send `ABORT` to stop the run.",
    ]
    return "\n".join(lines)


# ── Main loop ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="EndToEndDev orchestrator")
    parser.add_argument("--profile", default=None, help="Override ACTIVE_PROFILE")
    args = parser.parse_args()

    active_profile = args.profile or os.getenv("ACTIVE_PROFILE", "coder-v2")
    tasks = load_master_plan()

    if not tasks:
        print("[Main] No unchecked tasks found in brain/MASTER_PLAN.md (look for '- [ ]' lines).")
        sys.exit(1)

    print(f"[Main] Loaded {len(tasks)} tasks. Profile: {active_profile}")
    print(f"[Main] First task: {tasks[0]}")

    app = create_graph()
    import time
    config = {"configurable": {"thread_id": f"run-{int(time.time())}"}}

    initial_state: AgentState = {
        "step_number": 1,
        "total_steps": len(tasks),
        "current_task": tasks[0],
        "remaining_tasks": tasks[1:],
        "active_profile": active_profile,
        "gemini_session_id": None,
        "claude_session_id": None,
        "gpt_verdict": None,
        "claude_audit": None,
        "last_error": None,
        "loop_count": 0,
        "ceo_interrupt_flag": False,
        "session_turn_count": 0,
        "current_arch_layer": None,
        "ceo_instruction": None,
    }

    # `input_state` is the initial state on first call, None on resume.
    input_state = initial_state

    while True:
        print(f"\n[Main] Streaming graph (input={'initial' if input_state else 'resume'})...")

        for event in app.stream(input_state, config, stream_mode="updates"):
            node_name = list(event.keys())[0] if event else "unknown"
            print(f"  ↳ [{node_name}] done")

        # After stream exhausts, check if we're paused at an interrupt
        snapshot = app.get_state(config)

        if "ceo_review" in (snapshot.next or []):
            # Graph is paused before ceo_review — get CEO input
            current_state = snapshot.values
            alert_msg = format_ceo_alert(current_state)

            try:
                ceo_reply = ceo_comms.wait_for_reply(alert_msg, timeout=3600)
            except TimeoutError as e:
                print(f"[Main] {e} — aborting run.")
                break

            if ceo_reply.strip().upper() == "ABORT":
                print("[Main] Aborted by CEO.")
                break

            # Inject reply into state, then resume
            app.update_state(config, {"ceo_instruction": ceo_reply}, as_node="ceo_review")
            input_state = None  # None = resume from checkpoint
            continue

        # No interrupt — graph ran to completion (END or no next nodes)
        print("[Main] Graph run complete. Step finished.")
        break


if __name__ == "__main__":
    main()
