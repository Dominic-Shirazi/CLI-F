# Antigravity Analysis: Yielding the True Power of CLI Sessions

Based on a review of [EndToEndDev_Project_bible_v2.md](file:///c:/Users/persi/Documents/EndToEndDev/EndToEndDev_Project_bible_v2.md), [Claude_CLI_Guide.md](file:///c:/Users/persi/Documents/EndToEndDev/Claude_CLI_Guide.md), and [Gemini_CLI_Guide.md](file:///c:/Users/persi/Documents/EndToEndDev/Gemini_CLI_Guide.md), here is a summary of features we are currently ignoring, but absolutely shouldn't.

### 1. Tool Approvals and the Risk of Subprocess Hangs (YOLO)
**The Problem:** If run as subprocesses, both CLIs will eventually attempt to use a tool (like `Bash` or `Edit`) and prompt the user with `[y/N]`. Because it's a subprocess without an interactive TTY mapped to the human user, **the system will freeze indefinitely waiting for input.**
**The Solution:**
*   **Gemini:** We MUST pass `--approval-mode=yolo` when calling the Gemini CLI from the Python orchestrator for the builder iterations.
*   **Claude:** We MUST pass `--allowedTools "Bash,Edit,Read,Grep,Glob"` to Claude. If we use the "dangerously skip" flag, we risk it doing chaotic things, but explicit allowance means it reviews the PR without getting stuck on a simple `cat` command.
*   **GPT-OSS Guidance:** GPT-OSS doesn't give approvals in real-time, it judges the *aftermath*. We should prompt GPT-OSS to strictly fail a step if Gemini runs destructive commands (like `git push` or `rm -rf /`) that aren't in the plan.

### 2. Environment Context & "The Onboarding Problem"
**The Problem:** Gemini has a fresh CLI session. It writes a test. It types `pytest`. It fails. Why? Because it didn't activate [venv/Scripts/activate](file:///c:/Users/persi/Documents/EndToEndDev/venv/Scripts/activate) first. It spends 5 loops rewriting perfectly good code because the test environment is misconfigured.
**The Solution:**
*   We need a `PROJECT_ONBOARDING.md` (or a dedicated block in [MASTER_PLAN.md](file:///c:/Users/persi/Documents/EndToEndDev/brain/MASTER_PLAN.md)) that acts as the absolute truth for the environment.
*   **Examples of rules for the repo that all AI's must follow:**
    *   *Rule 1:* "All Python tests must be prepended with `call venv\Scripts\activate.bat && ...`"
    *   *Rule 2:* "If the UI looks bad, fail the step. The user expects premium, modern styling."
    *   *Rule 3:* "Do not mock the database if the task requires integration testing."
    *   *Rule 4:* "Keep a clean workspace, put all test files in a .test_folder/ and remove them after the test is run successfully."

### 3. Native CLI Features We Ignored in V1
We over-engineered our Python wrapper, missing out on native CLI flags:
*   `--append-system-prompt-file` (Both): Instead of reading our markdown templates into Python strings and injecting them via the command line (which can cause escaping nightmares), we can just point the CLIs directly to [gemini_prompt_template.md](file:///c:/Users/persi/Documents/EndToEndDev/prompts/gemini_prompt_template.md).
*   `--output-format json` (Both): Parsing markdown blocks from `stdout` is brittle. By forcing JSON output from the CLIs, Python can cleanly extract the required fields (like the reasoning or the Claude verdict).
*   `--max-turns` & `--max-budget-usd` (Claude): Claude can get stuck in loops with itself. Capping it at `--max-turns 3` protects the wallet and forces a timeout if it can't quickly audit the diff.
*   Claude `--json-schema` for validated structured output
`claude -p --json-schema '{"type":"object","properties":{"severity":{"enum":["CRITICAL","MINOR","NONE"]},...}}' "query"`
This gives **schema-validated JSON** output — better than `--output-format json` alone because Claude's response is guaranteed to match the schema. Use this for the auditor node so CRITICAL detection is based on a real structured field, not a string search on `**severity:**`.

Notes from Claude and Dominic:
Claude said:
Gemini `--output-format json` + `reasoning.md` — pick one
The V2 Bible expects Gemini to write `reasoning.md` to disk AND have its stdout parsed. In subprocess mode you can only do one cleanly. Decision:
- **Use `--output-format json`** for python to parse Gemini's verdict/reasoning from stdout
- Gemini still writes project files to disk (that's its main job)
- `reasoning.md` becomes the `reasoning` field in the JSON response, written to disk by the orchestrator
Dominic Thinks: Can't our system prompt Tell Gemini to do this? Then tell Gemini to output JSON response via flag to receiving something like: 'ready' when it's ready, or with a one sentence to GPT-OSS if needed?

Claude said:
GPT-OSS needs concrete environment rules, not just verdicts
GPT-OSS should receive a `ENVIRONMENT_RULES` block in its prompt that includes things like:
```
ENVIRONMENT RULES (fail the step if Gemini violated any of these rules):
- All Python commands must have run inside the activated venv at venv/Scripts/activate
- Tests must have run with: call venv\Scripts\activate.bat && pytest
- Reasoning.md must exist and be non-empty -(this also needs to be checked programically to ensure it was updated after Gemini's last action)
- Flag QUESTION if Gemini says "I assumed" or "I think" about any requirement, or if it has a 'To Do' in reasoning.md that indicates something that should be covered within the current step wasn't.
```
This is how GPT-OSS becomes the vibe-gatekeeper, not just a spec-checker.
(Dominic already modified this to his liking)

## 📋 Recommended CLI Invocation Patterns for V2 (From Claude and modified/updated by Dominic)

**Gemini Builder (first call):**
```bash
gemini --approval-mode=yolo --output-format json "{task_prompt}"
```

**Gemini Builder (resume):**
```bash
gemini --approval-mode=yolo --output-format json -r "<session-id>" "{next_instruction}"
```

**Claude Auditor:**
```bash
claude -p \
  --tools "Read,Grep,Glob,Bash(git diff *),Bash(git log *)" \   -(Dominic's note: shouldn't the git-diff be generated by python? why waste tokens having the AI do something we know it needs?)
  --json-schema '{audit_schema}' \
  --max-turns 10 \
  --max-budget-usd 0.50 \   -(Dominic's note: this is unnecessary, for when logged in to a pro account, unless limits have been reached)
  --session-id "{run_uuid}" \
  "{audit_prompt}"
```

**On Claude session resume (targeted fix loop):** (same considerations from Dominic here)
```bash
claude -p \
  --tools "Read,Grep,Glob,Bash(git diff *)" \
  --json-schema '{audit_schema}' \
  --max-turns 5 \
  -r "{run_uuid}" \
  "{targeted_fix_request}"
```

---

## 🏗️ Onboarding Architecture (Pre-Build Requirement)

Before any project run starts, the orchestrator must generate/confirm:

1. `GEMINI.md` — Gemini's project context file (venv rules, forbidden ops, project structure)
2. `CLAUDE.md` — Claude's project context file (audit focus, output format, escalation rules)
3. `brain/ENVIRONMENT_RULES.md` — injected into GPT-OSS brief (test commands, venv path, quality bars)
4. `brain/SUCCESS_CRITERIA.md` — per-step definitions of done

These four files are the "onboarding." The CEO fills them in (or approves Gemini generating them) before the loop starts. Without them, the loop runs blind.

---

*Analysis v2 — Claude Code (Lead Dev) additions to Gemini Antigravity's initial draft*

Additional Dominic Notes and thoughts:
we need to add the reasoning.md files and EndToENdDev related files within a repo to the gitignore file so they're not part of the dif logs every time and the reasoning md files are only read once intentionally, no t a second time as a git-diff

1. We need to add the reasoning.md files and EndToENdDev related files within a repo to the gitignore file so that they're not part of the dif logs every time and the reasoning md files are only read once intentionally, no t a second time as a git-diff.
2. .test_folder/ should be added to the gitignore file as well.

---

### Antigravity's Final Synthesis (For Claude's Review)

Dominic brings up a critical point regarding **Git Hygiene and State Isolation**. If we don't strictly separate the agent's internal workings from the project's source code, Claude and GPT-OSS will be analyzing polluted diff logs.

If we combine Dominic's requirements with my initial analysis, here is the coherent blueprint for the V2 orchestrator updates:

**1. Unblocking Automation (The Subprocess Problem):**
CLI prompts stall Python subprocesses. We must enforce `--approval-mode=yolo` for Gemini to prevent terminal hangs. For Claude, we inject explicit boundaries using `--allowedTools "Bash,Edit,Read,Grep,Glob"`, preventing deadlock on basic reads while keeping destructive capabilities in check.

**2. State Isolation via Git Ignore (Dominic's Core Requirement):**
The `git diff --stat` output must *only* reflect intentional codebase changes. To achieve this, the orchestrator must automatically ensure the target repository's `.gitignore` contains:
*   `workspace/gemini_output/reasoning.md`
*   `current_task.md`
*   `.test_folder/`
This guarantees Claude and GPT-OSS evaluate the pure code contribution, not the agent's scratchpad.

**3. Environment Context & Onboarding:**
Gemini needs strict guardrails on *how* to execute validation steps. A "Rules of Engagement" block in the prompt (or an `ONBOARDING.md`) must explicitly require environment activation (e.g., `venv/Scripts/activate`) and mandate that all temporary test scripts are created *only* within the `.test_folder/` (and deleted upon success, and after claude reviews the changes, test logs and test files).

**4. Optimizing the Python to CLI Bridge:**
Avoid injecting massive markdown templates as shell string arguments. We should utilize native CLI flags like `--system-prompt-file [path]` to initialize contexts cleanly. Furthermore, forcing `--output-format json` (where supported) will future-proof the orchestrator's parsing logic.

*Claude, please review the combined insights above and formulate the final step-by-step implementation guide to refactor the orchestrator.*
