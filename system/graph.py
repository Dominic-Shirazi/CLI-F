import os
import shutil
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from system.state import AgentState
from system.nodes.gemini_node import build_gemini_node
from system.nodes.inspector_node import build_inspector_node
from system.nodes.auditor_node import build_auditor_node
from system.git_ops import commit_step
from system.agent_runner import run_role, _log_event

# Mock reporter since it hasn't been implemented in V2 yet, but is referenced in the guide.
try:
    from system.reporter import build_reporter
except ImportError:
    def build_reporter(state: AgentState) -> None:
        pass

def ceo_review_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes AFTER main.py has injected ceo_instruction via app.update_state().
    Parses PASS / REJECT / free-text and sets ceo_route accordingly.
    """
    instruction = (state.get("ceo_instruction") or "").strip()
    upper = instruction.upper()

    if upper.startswith("PASS"):
        note = instruction[4:].lstrip(": ").strip()
        return {
            "ceo_route": "pass",
            "last_error": f"CEO note for auditor: {note}" if note else None,
            "loop_count": 0,
        }
    elif upper.startswith("REJECT"):
        note = instruction[6:].lstrip(": ").strip()
        return {
            "ceo_route": "reject",
            "last_error": f"CEO feedback: {note}" if note else "CEO rejected — fix the issues and try again.",
            "loop_count": 0,
        }
    elif upper.startswith("SKIP"):
        note = instruction[4:].lstrip(": ").strip()
        return {
            "ceo_route": "skip",
            "last_error": None,
            "loop_count": 0,
        }
    else:
        # Free-text treated as a Gemini instruction (old behaviour)
        return {
            "ceo_route": "reject",
            "last_error": f"CEO instruction: {instruction}",
            "loop_count": 0,
        }


def route_post_ceo(state: AgentState) -> Literal["auditor_node", "gemini_node", "step_approved", "end"]:
    """Route after CEO node: PASS→auditor, SKIP→step_approved, REJECT/other→Gemini."""
    instruction = (state.get("ceo_instruction") or "").strip().upper()
    if instruction == "ABORT":
        return "end"
    route = state.get("ceo_route", "reject")
    if route == "pass":
        return "auditor_node"
    if route == "skip":
        return "step_approved"
    return "gemini_node"

def step_approved_node(state: AgentState) -> Dict[str, Any]:
    """Post-audit success routing: commits step, updates architecture log, archives status, preps next."""
    step_num = state.get("step_number", 0)
    task_name = state.get("current_task", f"Step {step_num}")
    claude_session_id = state.get("claude_session_id")
    remaining_tasks = list(state.get("remaining_tasks") or [])

    # 1. Commit Step
    commit_step(f"Step {step_num}: {task_name}")

    # 2. Update AGENTS.md
    prompt = f"We just completed Step {step_num}: {task_name}. Based on your review of this step, append any new architectural or ecosystem learnings to our brain/AGENTS.md file. Only output the lines to append. If nothing new, output 'NONE'."
    try:
        run_role("reviewer", prompt, session_id=claude_session_id, max_turns=3, state=state)
    except Exception as e:
        print(f"Failed to update AGENTS.md: {e}")

    # 3. Reporter (Placeholder)
    build_reporter(state)

    # 4. Archive Status
    status_path = os.path.join("status", "STATUS_UPDATE.md")
    archive_dir = os.path.join("status")
    os.makedirs(archive_dir, exist_ok=True)
    if os.path.exists(status_path):
        shutil.copy2(status_path, os.path.join(archive_dir, f"step-{step_num}-summary.md"))

    _log_event("STEP_APPROVED | Task completion committed")

    # 5. Advance to next task if available
    if remaining_tasks:
        next_task = remaining_tasks[0]
        new_remaining = remaining_tasks[1:]
    else:
        next_task = "All tasks complete."
        new_remaining = []

    return {
        "step_number": step_num + 1,
        "loop_count": 0,
        "session_turn_count": 0,
        "gemini_session_id": None,
        "current_task": next_task,
        "remaining_tasks": new_remaining,
        "last_error": None,
    }


def route_post_step_approved(state: AgentState) -> Literal["gemini_node", "end"]:
    """After a step is approved: continue to next task or end if no tasks remain."""
    remaining = state.get("remaining_tasks") or []
    # current_task was already advanced in step_approved_node
    current_task = state.get("current_task", "")
    if remaining or (current_task and current_task != "All tasks complete."):
        return "gemini_node"
    return "end"


def route_post_inspector(state: AgentState) -> Literal["auditor_node", "gemini_node", "ceo_review"]:
    """Routing logic after the inspector returns a verdict."""
    verdict_line = state.get("gpt_verdict", "").strip()
    
    if verdict_line.startswith("QUESTION:"):
        return "ceo_review"
        
    if verdict_line.startswith("PASS") or verdict_line.startswith("REVIEW_REQUESTED"):
        return "auditor_node"

    loop_count = state.get("loop_count", 0)
    if loop_count >= 3:
        return "ceo_review"
        
    if verdict_line.startswith("INCOMPLETE:") or verdict_line.startswith("FAIL:"):
        # Tell gemini what went wrong without changing its session (it will fix it)
        return "gemini_node"
        
    # Fallback to CEO review if unrecognized verdict format occurs
    return "ceo_review"


def route_post_auditor(state: AgentState) -> Literal["step_approved", "gemini_node", "ceo_review"]:
    """Routing logic after Claude audits the code."""
    audit = state.get("claude_audit", {})
    severity = audit.get("severity", "CRITICAL")
    
    if severity == "CRITICAL":
        return "ceo_review"
        
    if severity in ["MAJOR", "MINOR"]:
        # Send back to Gemini for targeted fix.
        return "gemini_node"
        
    if severity == "NONE":
        return "step_approved"
        
    return "ceo_review"


def create_graph() -> StateGraph:
    """Initializes and wires the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("gemini_node", build_gemini_node)
    workflow.add_node("inspector_node", build_inspector_node)
    workflow.add_node("auditor_node", build_auditor_node)
    workflow.add_node("step_approved", step_approved_node)
    workflow.add_node("ceo_review", ceo_review_node)

    # Entry point: conditional so --review / --inspect can skip ahead
    def route_entry(state: AgentState) -> str:
        return state.get("start_at") or "gemini_node"

    workflow.add_conditional_edges(
        START,
        route_entry,
        {
            "gemini_node": "gemini_node",
            "inspector_node": "inspector_node",
            "auditor_node": "auditor_node",
        },
    )
    workflow.add_edge("gemini_node", "inspector_node")
    
    workflow.add_conditional_edges(
        "inspector_node",
        route_post_inspector,
        {
            "auditor_node": "auditor_node",
            "gemini_node": "gemini_node",
            "ceo_review": "ceo_review"
        }
    )
    
    workflow.add_conditional_edges(
        "auditor_node",
        route_post_auditor,
        {
            "step_approved": "step_approved",
            "gemini_node": "gemini_node",
            "ceo_review": "ceo_review"
        }
    )
    
    workflow.add_conditional_edges(
        "step_approved",
        route_post_step_approved,
        {
            "gemini_node": "gemini_node",
            "end": END,
        }
    )

    workflow.add_conditional_edges(
        "ceo_review",
        route_post_ceo,
        {
            "auditor_node": "auditor_node",
            "gemini_node": "gemini_node",
            "step_approved": "step_approved",
            "end": END,
        },
    )

    # Memory saver for state checkpointing
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory, interrupt_before=["ceo_review"])
