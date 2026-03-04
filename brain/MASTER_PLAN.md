# MASTER_PLAN.md — Project Genesis Tool

## Vision
A standalone tool that lets any developer describe their project idea to a web AI
(Gemini Web, ChatGPT, Claude.ai) via a single prompt document. The AI conducts a
structured interview, then generates a complete set of EndToEndDev-ready files
packaged as a zip. The developer drops the zip into a folder, runs deploy.py, and
the EndToEndDev loop is ready to start building their project.

## Why This Exists
Starting a new EndToEndDev project requires manually writing MASTER_PLAN.md, GEMINI.md,
CLAUDE.md, SUCCESS_CRITERIA.md, and profile configs — all in very specific formats the
agents depend on. This is a cold-start problem that blocks adoption. Genesis solves it:
ANY web AI can conduct the interview and generate perfectly-formatted files with zero
local tooling. No API keys. No setup. Paste, chat, download zip, run deploy.py.

## What "Done" Looks Like (CEO walkthrough)
1. CEO opens Gemini Web (or ChatGPT, Claude.ai — any web AI)
2. Pastes the contents of tools/project_genesis/GENESIS_PROMPT.md into the chat
3. The AI introduces itself as a "Project Architect" and begins asking questions
   one topic group at a time — conversationally, not all at once
4. After ~20-40 minutes of Q&A, CEO says "generate" (or similar)
5. The AI outputs a zip file download containing all required project files
6. CEO drops the zip into tools/project_genesis/drop_zone/
7. CEO runs: python tools/project_genesis/deploy.py
8. deploy.py validates, extracts, and places files in the correct locations
9. CEO opens .env, fills in API keys, and runs: python main.py
10. EndToEndDev starts building the CEO's project from Step 1

## Architecture

```
tools/
└── project_genesis/
    ├── GENESIS_PROMPT.md      # Paste into any web AI — the full interviewer prompt
    ├── deploy.py              # Validates and extracts the AI-generated zip
    ├── drop_zone/             # Drop the zip here before running deploy.py
    │   └── .gitkeep
    └── README.md              # 5-line usage instructions
```

## Files the AI Must Generate (what deploy.py validates and places)

| File in zip | Destination in project |
|---|---|
| MASTER_PLAN.md | brain/MASTER_PLAN.md |
| SUCCESS_CRITERIA.md | brain/SUCCESS_CRITERIA.md |
| ENVIRONMENT_RULES.md | brain/ENVIRONMENT_RULES.md |
| CLAUDE.md | CLAUDE.md |
| GEMINI.md | GEMINI.md |
| env.example | .env.example |
| project-default.json | system/profiles/project-default.json |
| writer.md | prompts/standard/writer.md |
| inspector.md | prompts/standard/inspector.md |
| reviewer.md | prompts/standard/reviewer.md |

## Environment
- OS: Windows 11
- Python: 3.12
- Virtual environment: venv/ (activate: venv\Scripts\activate)
- Project root: C:\Users\persi\Documents\EndToEndDev (forked copy)
- All test commands must use the activated venv
- Write all temp/test artifacts to .test_folder/ — delete after passing test

## Reference Files (read these to understand the target file formats)
Gemini: before writing any output files, read these existing files in the repo to
understand what each generated file must look like:
- CLAUDE.md — the auditor role/schema format
- GEMINI.md — the writer rules format
- brain/ENVIRONMENT_RULES.md — the inspector rules format
- brain/SUCCESS_CRITERIA.md — the step-done criteria format
- system/profiles/coder-v2.json — the profile JSON schema
- prompts/standard/writer.md — the writer prompt format
- prompts/standard/reviewer.md — the reviewer prompt format

---

## Build Steps

- [ ] Step 1: Complete Master_Plan_requirements.md
  Write the full question list to Master_Plan_requirements.md (in the repo root).
  Organize into 9 topic groups. Each group needs a heading and 3-6 specific questions
  that a web AI would ask a developer about a new project. Questions must be concrete
  and actionable — no vague ones like "describe your project." This document becomes
  the canonical question reference embedded inside GENESIS_PROMPT.md in Step 2.
  Test: the file exists, has all 9 groups, and has at least 35 total questions.

- [ ] Step 2: Write tools/project_genesis/GENESIS_PROMPT.md — Part 1 (Interviewer Setup)
  Create tools/project_genesis/ directory. Write the first half of GENESIS_PROMPT.md:
  the system context block (what EndToEndDev is, what files it needs, why they matter),
  the interviewer persona instructions (introduce as "Project Architect", ask one group
  at a time, confirm before moving on, be conversational not clinical), and the full
  question list embedded from Master_Plan_requirements.md.
  Do NOT write the output/generation section yet — that is Step 3.
  Test: file exists, has system context, interviewer instructions, and all 9 question
  groups. Word count should be 600-1200 words (substantial but not bloated).

- [ ] Step 3: Write tools/project_genesis/GENESIS_PROMPT.md — Part 2 (Output Section)
  Append the output generation section to GENESIS_PROMPT.md. This section must:
  - Tell the AI when/how the CEO signals they are ready to generate (say "GENERATE")
  - Specify exactly what 10 files to produce and each file's required content/schema
    (read the reference files listed above to write accurate schemas)
  - For each file: give the AI a filled-in template showing format, section headings,
    and placeholder tokens like {{PROJECT_NAME}}, {{LANGUAGE}}, {{STEP_LIST}}, etc.
  - Instruct the AI to package all 10 files as a single zip download named
    genesis_output.zip with no subdirectories (flat structure inside the zip)
  - Add a closing note: "After the CEO downloads the zip, they run deploy.py to install."
  Test: GENESIS_PROMPT.md contains the word "GENERATE", contains all 10 filenames,
  contains placeholder tokens, and contains zip packaging instructions.

- [ ] Step 4: Write tools/project_genesis/deploy.py
  A standalone Python script (no dependencies beyond stdlib). When run from the project
  root, it:
  1. Looks for exactly one .zip file in tools/project_genesis/drop_zone/
  2. Validates the zip contains all 10 required files (listed in Architecture table above)
  3. Prints a clear error and exits if any required file is missing
  4. Extracts each file to its destination path (see Architecture table), creating
     directories as needed
  5. Prints "✓ <filename> → <destination>" for each file placed
  6. Prints a final success message with next steps (.env and python main.py)
  7. Does NOT overwrite existing files without --force flag
  Test: create a fixture zip in .test_folder/ containing all 10 required files (empty
  content), run deploy.py --dry-run (add this flag: validate and print but don't write),
  confirm it exits 0 and lists all 10 files. Delete fixture after passing test.

- [ ] Step 5: Create drop_zone and README
  Create tools/project_genesis/drop_zone/.gitkeep (empty file).
  Write tools/project_genesis/README.md with exactly these sections:
  - What is Genesis? (2 sentences)
  - How to use it (numbered steps matching the CEO walkthrough in this MASTER_PLAN)
  - What gets generated (the 10-file table from the Architecture section)
  - Troubleshooting (3 common errors deploy.py might print and what to do)
  Test: both files exist. README.md has all 4 sections. .gitkeep is empty.
