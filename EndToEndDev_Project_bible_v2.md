# EndToEndDev — Architecture V2
### "Vibe-First" Redesign: CLI Agents with Native Sessions

---

## WHAT CHANGED AND WHY

The V1 design treated Gemini and Claude like dumb API endpoints — manually injecting context, managing memory, and carrying state that the CLI tools already handle natively. We were doing the AI's job for it.

**V2 Philosophy:** The CLI tools are the agents. They have full sessions, memory, state and TOOLS too. We should be using them to their full potential, Consider what they can do for us, use them to their maximum potential. LangGraph is the traffic cop. Python handles the mechanical stuff (git, file reads, status reports, prompts). GPT-OSS is the quality gate and vibe boss. GPT-OSS should act as the vibe-coder, Gemini should act as the code-coder, Claude should act as the design-engineer and git-reviewer.
---

## THE 5 DESIGN DECISIONS

---

### Decision 1 — Gemini/Claude Session Flags ✅ CONFIRMED

Gemini CLI supports native sessions  as does Claude CLI - see @Gemini_CLI_Guide.md and @Claude_CLI_Guide.md for details and all potential flags/options. We should be using the native sessions for both agents. 

We should also be considering using additional flags, and making our system a power-user of the CLI tools. 

**Implementation:** LangGraph stores the `session_id` (index number) in `AgentState` after the first Gemini call. Every subsequent call passes `--resume {session_id}`. Claude CLI uses --continue, or -c (Loads the most recent conversation in the current directory) example use: 'claude --continue'

**Result:** Both agents maintain their own conversational memory natively. No manual context injection. No changelog history stuffing. Just the next instruction.

---

### Decision 2 — Session Crash Recovery Strategy ✅ DEFINED

**Happy path:** LangGraph checkpoint saves `session_id`. Graph resumes. CLI resumes via `--resume {session_id}`. Everything continues.

**If session resumption fails** (session expired or CLI garbage-collected it), the node falls back to a **"Cold Start Recovery Prompt"**:

```
Session recovery initiated.
Read the following to get your bearings:
- MASTER_PLAN.md (your mission)
- workspace/gemini_output/reasoning.md (what Gemini last said it did)
- workspace/audit_trail/ceo_decisions/decision_log.md (what Claude last said it did)
- The git file manifest below (what actually changed)

Current step: {step_number} of {total_steps}
Last known error: {last_error}

Continue from where you left off.
```

The agent reads the files, figures out where it is, and keeps going. No human needed unless it fails twice in a row — then it pings the CEO.

---

### Decision 3 — What GPT-OSS Reads ✅ DEFINED

GPT-OSS receives a structured brief assembled entirely by Python (zero AI tokens):

```
## Inspector Brief — Step {N} of {TOTAL}

### The Mission (what this step was supposed to do)
{relevant excerpt from MASTER_PLAN.md}

### What Gemini Said It Did
{contents of workspace/gemini_output/reasoning.md}

### Files Changed (Python-generated, not AI-generated)
{git diff --stat output}
Example:
  src/auth/login.py     | 24 ++++++++++++++----------
  src/auth/logout.py    |  8 ++++----
  2 files changed, 32 insertions(+), 20 deletions(-)

### Inspector Decision Tree
Think critically. Then output ONLY one of the following:

PASS
  → Gemini's work matches the plan completely. Pass to Claude for audit.

INCOMPLETE: {one sentence on what's missing}
  → Gemini only finished part of the task. Send back to Gemini to continue.

QUESTION: {one sentence describing what Gemini is asking}
  → Gemini is requesting input before continuing. Ping the CEO.

REVIEW_REQUESTED
  → Gemini has flagged its own work for review. Pass to Claude.

FAIL: {one sentence on what's wrong}
  → The work doesn't match the plan at all. Send back to Gemini with correction.
```

**Key rules for GPT-OSS:**
- Output ONLY the verdict keyword + one sentence. Nothing else.
- Never hallucinate terminal commands. You receive file info, you don't run anything.
- If Gemini's reasoning.md says something like "Completed part 1 of this step" output `INCOMPLETE`.

---

### Decision 4 — Git Workflow ✅ DEFINED (Python-handled, zero AI tokens)

Git operations are handled entirely by Python in the orchestrator. No AI model touches git.

**The flow:**

At project begining, a git repo is created and the initial commit is made programmatically.
1. Gemini begins work on the current step, writing files directly into the workspace, and is directed to output in human readable english 'what it did' into reasoning.md in the workspace/gemini_output folder for GPT-OSS and Claude to review. 
2. GPT-OSS reviews Gemini's output — if incomplete or missing something, or if gemini didn't update reasoning.md, it sends Gemini back to finish. This loop repeats until GPT-OSS confirms the full step is done and all tasks complete. 
3. Once GPT-OSS signs off, Python runs git diff HEAD against unstaged changes and passes the full step diff to Claude for review along with gemini_output/reasoning.md for context. 
4. Claude reviews the complete step diff and writes it's output to reasoning.md in the workspace/Claude_output.md for Gemini to review. 
5. If Claude spots an issue → sends a specific targeted fix request back to Gemini (not a full rewrite)
6. Gemini reads workspace/Claude_output.md and applies the fix → GPT-OSS loop runs again to confirm the fix is complete → Claude re-reviews
7. This loop repeats until Claude is satisfied
8. Once Claude approves → Python runs git add -A and git commit -m "Step {N}: {task_name} — approved"
9. One clean commit per approved step. Git history = a perfect record of the build.
10. Step counter advances → next step begins

**Why Python handles this:** No hallucination risk, no token cost, deterministic behavior. The CEO never sees raw git output — just a clean file list in STATUS_UPDATE.md.

---

### Decision 5 — output/ Folder ✅ DEPRECATED

The `output/` folder is removed. It was a V1 artifact of the "single file approval" model.

**V2 reality:** Gemini writes directly into the project workspace. Git is the approval mechanism — a passing step = committed clean history. A failing step = auto-reverted.

**Also removed in V2:**
- `workspace/gemini_output/latest_code.md` (single-file bottleneck, gone)
- `USE_API_MODE` flag and all API SDK code (premature optimization, dead weight)
- Manual `changelog_history` injection (sessions handle this natively)

---

## UPDATED FOLDER STRUCTURE

```
EndToEndDev/
│
├── 📁 brain/
│   ├── MASTER_PLAN.md               # The mission. Never changes mid-run.
│   └── SUCCESS_CRITERIA.md          # How we know each step is done.
│
├── 📁 workspace/
│   ├── current_task.md              # The one step being worked on RIGHT NOW
│   └── gemini_output/
│       └── reasoning.md             # What Gemini says it just did and why
│
├── 📁 audit_trail/
│   ├── inspector_verdict.md         # Inspector: PASS / INCOMPLETE / FAIL / etc.
│   ├── claude_audit_notes.md        # Claude: CRITICAL / MINOR / NONE
│   └── ceo_decisions/
│       └── decision_log.md          # Timestamped log of every CEO call
│
├── 📁 status/
│   ├── STATUS_UPDATE.md             # Auto-generated sprint summary each loop
│   └── token_log.json               # Running Claude token count
│
├── 📁 prompts/
│   ├── standard/                    # Default prompt templates (coder-v2, local-only)
│   │   ├── writer.md
│   │   ├── inspector.md
│   │   └── reviewer.md
│   └── power/                       # Enhanced templates (power-inspector)
│       └── inspector.md             # Inspector with tool-use instructions
│
├── 📁 system/
│   ├── graph.py                     # LangGraph main loop
│   ├── agent_runner.py              # Profile-driven CLI abstraction (run_role API)
│   ├── profiles/                    # Role presets (version-controlled JSON)
│   │   ├── coder-v2.json            # Gemini + Ollama + Claude (default)
│   │   ├── local-only.json          # All Ollama, zero cloud calls
│   │   └── power-inspector.json     # Claude-powered Inspector with tools
│   ├── nodes/
│   │   ├── gemini_node.py           # Manages Writer CLI session lifecycle
│   │   ├── inspector_node.py        # Builds Inspector brief, calls via run_role()
│   │   └── auditor_node.py          # Manages Reviewer CLI session, parses audit
│   ├── git_ops.py                   # ALL git operations. Python only. No AI.
│   ├── state.py                     # Shared AgentState TypedDict (incl. active_profile)
│   └── checkpoints/
│       └── .keep
│
├── [your actual project files]      # Gemini writes here directly
│
├── .env                             # ACTIVE_PROFILE + session thresholds only
├── requirements.txt
└── README.md
```

---

## UPDATED LANGGRAPH FLOW (PLAIN ENGLISH)

```
START
  │
  ▼
LOAD NEXT STEP from MASTER_PLAN → write to current_task.md
  │
  ▼
╔══════════════════════════════════╗
║  NODE 1: GEMINI (Builder)        ║
║                                  ║
║  First run:  gemini {prompt}     ║
║  Resume:     gemini --resume {id}║
║                                  ║
║  Gemini writes files directly    ║
║  Gemini writes reasoning.md      ║
║  (Incl. reasoning, tests, logs)  ║
║  Session ID saved to AgentState  ║
╚══════════════╤═══════════════════╝
               │
               ▼
╔══════════════════════════════════╗
║  NODE 2: GPT-OSS (Inspector)     ║
║                                  ║
║  Reads: current_task.md          ║
║         reasoning.md             ║
║         workspace changes        ║
║  Outputs: ONE verdict keyword    ║
╚══════════════╤═══════════════════╝
               │
    ┌──────────┼──────────┬──────────┐
    │          │          │          │
PASS/REVIEW  INCOMPLETE  QUESTION     FAIL
    │          │          │          │
    │     Back to      Ping CEO   Back to
    │     Gemini                  Gemini
    │  (keep session)             (keep session)
    ▼
    Python: git add -A (staging)
    Python: git diff --stat → full step diff
               │
               ▼
╔══════════════════════════════════╗
║  NODE 3: CLAUDE (Auditor)        ║
║                                  ║
║  Reads: reasoning.md (test logs) ║
║         full step diff           ║
║         current_task.md          ║
║  Outputs: CRITICAL/MINOR/NONE    ║
╚══════════════╤═══════════════════╝
               │
    ┌──────────┼──────────┐
    │          │          │
CRITICAL     MINOR      NONE
    │          │          │
  PAUSE      Back to      │
  PING CEO   Gemini       │
 (interrupt) (targeted fix)▼
                   ✅ STEP APPROVED
                   Git commit finalized
                   STATUS_UPDATE.md generated
                   Advance step counter
                        │
                   More steps?
                   YES → loop | NO → 🎉 DONE
```

---

## UPDATED HANDOFF FORMATS

### Gemini → Inspector
**File:** `workspace/gemini_output/reasoning.md`
```markdown
## Reasoning — Step [N]
**What I was asked to do:** [quote the task]
**What I actually did:** [plain English summary]
**Tests Performed:** [path to test file and command used]
**Test Results:** [capture brief results, logs, or error snippets]
**Did I complete the full task?** YES / PARTIAL: [what's left] / NEEDS REVIEW: [why]
**Any questions before I continue?** NONE / QUESTION: [the question]
```

### Inspector → LangGraph
**File:** `audit_trail/inspector_verdict.md`
```
PASS
  → Move to Claude for audit.
```
or
```
REVIEW_REQUESTED: [reason]
  → Gemini flagged its own work. Move to Claude for audit.
```
or
```
INCOMPLETE: [one sentence — what's missing]
  → Back to Gemini in same session.
```
or
```
QUESTION: [one sentence — what Gemini is asking]
  → Pause for CEO input.
```
or
```
FAIL: [one sentence — what's wrong]
  → Back to Gemini in same session.
```

### Claude → LangGraph
**File:** `audit_trail/claude_audit_notes.md`
```markdown
## Audit — Step [N]
**Severity:** CRITICAL | MINOR | NONE
**Issue:** [one sentence]
**Why it matters:** [one sentence]
**Suggested fix:** [be brief, but specific, SAVE TOKENS]
```

### LangGraph → CEO
**File:** `status/STATUS_UPDATE.md`
```markdown
## Sprint Summary — Step [N] of [TOTAL]
**Result:** APPROVED ✅ | PENDING YOUR INPUT ⚠️
**Files changed this step:** [from git diff --stat]
**Inspector verdict:** [PASS / INCOMPLETE / etc.]
**Claude severity:** [CRITICAL / MINOR / NONE]
**Claude's note:** [paste from audit notes]
**Claude tokens this turn:** [N]
**Total Claude tokens used:** [N]
**Action required:** YES — [what you need to decide] | NO
```

---

## REFACTOR CHECKLIST FOR GEMINI ANTIGRAVITY

1. **Delete** `output/` folder and all references to it
2. **Delete** `workspace/gemini_output/latest_code.md`
3. **Delete** all API SDK code and `USE_API_MODE` from `.env` and nodes
4. **Delete** manual `changelog_history` injection from `gemini_node.py`
5. **Delete** per-role env vars (`WRITER_CLI`, `WRITER_MODEL`, etc.) — replaced by Profile system
6. **Create** `system/profiles/` directory with three preset JSON files: `coder-v2.json`, `local-only.json`, `power-inspector.json`
7. **Create** `system/agent_runner.py` — profile-driven `run_role()` API, `load_profile()`, `get_prompt_template()`, session refresh logic
8. **Create** `system/git_ops.py` with five functions: `init_repo()`, `get_diff_stat()`, `get_full_diff()`, `commit_step()`, `revert_uncommitted()`
9. **Reorganize** `prompts/` into subdirectories: `prompts/standard/` (writer, inspector, reviewer) and `prompts/power/` (enhanced inspector)
10. **Refactor** `gemini_node.py` — use `agent_runner.run_role("writer", ...)`, save session ID to state, implement cold-start recovery
11. **Refactor** `inspector_node.py` — use `agent_runner.run_role("inspector", ...)`, build brief from profile's prompt template + git manifest
12. **Refactor** `auditor_node.py` — use `agent_runner.run_role("reviewer", ...)`, parse CRITICAL/MAJOR/MINOR/NONE
13. **Update** `state.py` — add `active_profile: str` field
14. **Update** `graph.py` — add conditional edges for INCOMPLETE, QUESTION, REVIEW_REQUESTED, MAJOR
15. **Update** `.env.example` — single `ACTIVE_PROFILE=coder-v2` replaces all per-role vars

---

*Architecture V2.0 — EndToEndDev*
*CEO: Dominic | Lead Dev: Claude | Builder: Gemini Antigravity | Inspector: Configurable via Profile*