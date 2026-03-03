# Project Rules for Gemini CLI

## Environment
- This project runs on Windows. Always activate the related venv or conda env before running Python:
  `call venv\Scripts\activate.bat && <your command>` or `conda activate <env_name> && <your command>`
- Never run commands without the activated venv or conda env as indicated in the MASTER_PLAN.md

## What You Are Allowed To Do
- Read, create, edit, and delete files within the project workspace
- Run tests using pytest inside the activated venv
- Write all temporary test files to `.test_folder/` only, delete them after a passing test run

## What You Must Never Do
- `git push` — Python handles all git operations
- `git commit` — Python handles all git operations
- `rm -rf` on anything outside your assigned workspace

## Output Contract
After completing your task, you MUST write `workspace/gemini_output/reasoning.md` using this exact format:

### Reasoning — Step [N]
**What I was asked to do:** [quote the task]
**What I actually did:** [plain English summary]
**Tests Performed:** [command used - if any]
**Test Results:** [pass/fail + brief output - if any]
**Did I complete the full task?** YES / PARTIAL: [what's left] / NEEDS_REVIEW: [why]
**Any questions before I continue?** NONE / QUESTION: [the question]
