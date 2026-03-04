# EndToEndDev V3 Design Proposal: Remote CEO & Prompt Generation

This document outlines the proposed architecture for the next major iteration of EndToEndDev. Based on the user's requirements, we need to solve two distinct problems:
1. **Remote CEO Review**: Getting Human-In-The-Loop feedback when away from the terminal.
2. **Project Generation**: Creating robust `MASTER_PLAN.md` and agent instruction files from a set of high-level requirements.

---

## 1. Remote CEO Review (Human-In-The-Loop)

Currently, [system/graph.py](file:///c:/Users/persi/Documents/EndToEndDev/system/graph.py) halts execution via LangGraph's `interrupt_before=["ceo_review"]`. To make this remote, we need to build an outer orchestrator (e.g., `main.py`) that catches this interrupt and dispatches a notification.

### Proposed Integration: Telegram Bot
Telegram is natively asynchronous, free, and has a very straightforward Python API (`python-telegram-bot`), making it ideal for a "CEO" to receive and reply to text on the go.

**Architecture:**
- **`system/ceo_comms.py`**: A new module that handles sending the "CRITICAL ERROR" state to a Telegram chat.
- **Workflow**:
  1. LangGraph hits the [ceo_review](file:///c:/Users/persi/Documents/EndToEndDev/system/graph.py#21-24) node and pauses.
  2. The outer orchestrator detects the pause and reads the [AgentState](file:///c:/Users/persi/Documents/EndToEndDev/system/state.py#3-17).
  3. `ceo_comms.sendMessage(f"CEO Review Required: {severity} - {issue}\nReply with instructions.")`
  4. The orchestrator enters a polling loop (or uses a webhook) waiting for the CEO'm message.
  5. User replies via Telegram.
  6. Orchestrator receives the reply, injects it into the State, and calls `app.stream(None, config)` to resume the graph.

*Alternative (Tailscale/SSH)*: We could run a lightweight Flask/FastAPI server bound to a Tailscale IP, serving a simple HTML form to review the state. Telegram is generally faster for push notifications. Let's ask Claude which he prefers.

---

## 2. Project Blueprints & Prompt Generation

The user has provided [Master_Plan_requirements.md](file:///c:/Users/persi/Documents/EndToEndDev/Master_Plan_requirements.md). We need a tool that takes these raw requirements and generates the robust files needed to seed a new EndToEndDev loop.

Our system currently relies on:
- `MASTER_PLAN.md` (The step-by-step checklist)
- `system/profiles/*.json` (Agent routing)
- `prompts/standard/*.md` (Agent instructions)

### Proposed Tool: `tools/project_bootstrap.py`
A standalone script that uses Gemini (via its native API) to transform a raw requirements document into the structured files V2 needs.

**Workflow:**
1. User writes a raw `idea_pitch.md` (or fills out a Q&A form answering the requirements from [Master_Plan_requirements.md](file:///c:/Users/persi/Documents/EndToEndDev/Master_Plan_requirements.md)).
2. Run `python tools/project_bootstrap.py idea_pitch.md`.
3. The script asks Gemini to output three things:
   - A highly detailed `MASTER_PLAN.md` broken into literal `Phase X: Step Y` checkboxes.
   - A targeted set of `system/profiles/` (e.g., choosing `coder-v2.json` or creating a custom one mapping specific models).
   - Custom `prompts/` (e.g., `feature_writer.md`) that embeds the environment context (Python version, venv, target audience, UI aesthetics).
4. The script saves these files, ready for `main.py` to start processing them.

### Content of the Bootstrapped MASTER_PLAN.md
Based on the user's notes, the generated plan *must* include:
- **Environment Block**: Python 3.12, node 20, venv commands.
- **Hardware/API Block**: Target device specs, API endpoint lists.
- **Vision Block**: Plain english "Why" and "What it looks like".
- **Architecture Block**: Folder structure and data flow.
- **Execution Block**: Step-by-step checkboxes (the actual tasks).
- **Testing Block**: Edge case test instructions.

---

## Next Steps for Claude Review
Claude, please review this V3 proposal.
1. Do you agree with Telegram for the Remote CEO integration, or is there a better architecture for pausing/resuming LangGraph remotely?
2. Does the `project_bootstrap.py` approach make sense for generating the `MASTER_PLAN.md` and prompt templates off a single requirement file?


# Dominic's Notes
## Thought 1
  I was thinking of dropping the md file into gemini web, then gemini web would generate a zip file with the files necessary, then we make a folder called 'drop_zip_file_here/' or something obvious, then we pythonically unzip and move the files to the right place and a .exe to run it all? 
## Thought 2
