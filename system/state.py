from typing import TypedDict, Optional, List

class AgentState(TypedDict):
    step_number: int
    total_steps: int
    current_task: str
    remaining_tasks: List[str]
    active_profile: str                  # Name of the active profile (e.g., "coder-v2")
    gemini_session_id: Optional[str]    # "latest" after first call, or None on fresh step
    claude_session_id: Optional[str]    # UUID generated once at run start, kept across steps
    gpt_verdict: Optional[str]          # PASS / FAIL / INCOMPLETE / QUESTION / REVIEW_REQUESTED
    claude_audit: Optional[dict]        # Parsed JSON: {severity, issue, why_it_matters, suggested_fix}
    last_error: Optional[str]
    loop_count: int
    ceo_interrupt_flag: bool
    session_turn_count: int             # Incremented each time the writer CLI is called
    current_arch_layer: Optional[str]   # e.g., "backend", "frontend", "infra" — for refresh trigger
    ceo_instruction: Optional[str]      # Reply injected by main.py after Telegram/terminal input
    ceo_route: Optional[str]            # "pass" | "reject" | "skip" — set by ceo_review_node, read by router
    start_at: Optional[str]             # Override entry node: "gemini_node" (default) | "auditor_node" | "inspector_node"
