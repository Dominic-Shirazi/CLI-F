# EndToEndDev 2.0 Autonomous Loop

This system runs a completely autonomous coding loop governed by LangGraph. It is designed to be profile-driven, meaning the specific models, CLIs, and prompts used for the writer, inspector, and auditor nodes can be entirely customized via JSON profiles.

The loop relies on native CLI session persistence (`gemini --resume`, `claude --continue`) so the AI context remains intact over the course of multiple loops and steps, drastically reducing token burn and improving project awareness.

## V2 Architecture

1. **Profile System:** Custom profiles (`system/profiles/*.json`) dictate how `system/agent_runner.py` executes nodes. You can run all nodes locally via Ollama, or use API-backed CLIs like Gemini and Claude.
2. **Session Persistence:** Models maintain long-running CLI sessions across the graph execution.
3. **Python-Handled Git:** The AI nodes never run `git commit`. The system handles checkpointing steps upon auditor approval, ensuring a pristine git history.
4. **Memory:** Long-term memory is maintained in `brain/AGENTS.md` (architectural learnings appended by Claude) and `brain/progress.txt` (event log).
5. **Onboarding Requirements:** The agents rely on root-level identity rules (`GEMINI.md`, `CLAUDE.md`) to define their boundaries. 

## Installation Instructions

1. **Install Python Packages:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Select or Create a Profile:**
   Copy `.env.example` to `.env` and set `ACTIVE_PROFILE=coder-v2` (or your preferred JSON profile name).
   ```bash
   cp .env.example .env
   ```

3. **Install Required CLIs:**
   Ensure the CLIs specified in your active profile are accessible in your system path (e.g., `gemini`, `claude`, `ollama`).

## Getting Started

To start a run from the beginning of `brain/MASTER_PLAN.md`:

```bash
python system/graph.py
```

## Crash Recovery

LangGraph uses a SQLite checkpointer (`system/checkpoints/langgraph_checkpoints.sqlite`), so resuming after a crash or stoppage is fully supported. 

## Responding to a CEO Interrupt

If the LangGraph loop pauses due to a **CRITICAL** severity audit finding from Claude, or if the inspector hits the infinite loop guard, it will wait for your input. 

1. Review the generated `audit_trail/claude_audit_notes.md` or the inspector verdict in `audit_trail/inspector_verdict.md`.
2. Review the code diff via `git diff HEAD`.
3. Provide feedback or manually fix the issue before resuming the graph.
