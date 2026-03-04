import os
import shutil
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
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
    Forwards the CEO's reply to Gemini as last_error so it knows what to do next.
    """
    instruction = state.get("ceo_instruction") or "No instruction provided."
    return {
        "last_error": f"CEO instruction: {instruction}",
        "loop_count": 0,  # reset loop guard on CEO intervention
    }


def route_post_ceo(state: AgentState) -> Literal["gemini_node", "end"]:
    """After CEO node: ABORT stops the graph, anything else goes back to Gemini."""
    instruction = (state.get("ceo_instruction") or "").strip().upper()
    if instruction == "ABORT":
        return "end"
    return "gemini_node"

def step_approved_node(state: AgentState) -> Dict[str, Any]:
    """Post-audit success routing: commits step, updates architecture log, archives status, preps next."""
    step_num = state.get("step_number", 0)
    task_name = state.get("current_task", f"Step {step_num}")
    claude_session_id = state.get("claude_session_id")

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

    # 5. Load Next Task (Placeholder for now, assuming external loop handles pulling MASTER_PLAN.md)
    # 7. Append Event
    _log_event("STEP_APPROVED | Task completion committed")

    # 6 & 8. Reset specific state attributes for the next node
    return {
        "step_number": step_num + 1,
        "loop_count": 0,
        "session_turn_count": 0,
        "gemini_session_id": None, # Clean writer session
        "current_task": "Awaiting next task from MASTER_PLAN.md",
        "last_error": None
    }


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

    # Edges
    workflow.set_entry_point("gemini_node")
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
    
    workflow.add_edge("step_approved", END)

    workflow.add_conditional_edges(
        "ceo_review",
        route_post_ceo,
        {
            "gemini_node": "gemini_node",
            "end": END,
        },
    )

    # Memory saver for state checkpointing
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory, interrupt_before=["ceo_review"])
