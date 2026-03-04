# SUCCESS_CRITERIA.md — Project Genesis Tool

Each step is DONE only when ALL criteria below are met.
The Inspector checks these against reasoning.md and the git diff.

---

## Step 1: Complete Master_Plan_requirements.md
- [ ] Master_Plan_requirements.md exists in repo root
- [ ] File contains exactly 9 topic group headings
- [ ] File contains at least 35 numbered questions total
- [ ] No group has fewer than 3 questions
- [ ] No vague questions (must be specific enough for a developer to answer in one sentence)
- [ ] reasoning.md confirms the file was written, not edited from a template

## Step 2: GENESIS_PROMPT.md — Part 1 (Interviewer Setup)
- [ ] tools/project_genesis/ directory created
- [ ] tools/project_genesis/GENESIS_PROMPT.md exists
- [ ] File contains a system context block explaining what EndToEndDev is
- [ ] File contains interviewer persona instructions (one group at a time, conversational)
- [ ] All 9 question groups from Master_Plan_requirements.md are present
- [ ] File does NOT yet contain the output/generation section (that is Step 3)
- [ ] Word count between 600 and 1200

## Step 3: GENESIS_PROMPT.md — Part 2 (Output Section)
- [ ] GENESIS_PROMPT.md contains the trigger word "GENERATE"
- [ ] Output section lists all 10 required filenames
- [ ] Each file has a filled-in template with placeholder tokens (e.g., {{PROJECT_NAME}})
- [ ] Zip packaging instruction is present (flat structure, named genesis_output.zip)
- [ ] Schemas match the format of the reference files in the repo (read them first)
- [ ] Closing next-steps note is present

## Step 4: deploy.py
- [ ] tools/project_genesis/deploy.py exists
- [ ] Script uses only Python stdlib (no pip installs required)
- [ ] Handles drop_zone/ with exactly one zip (errors clearly if zero or multiple)
- [ ] Validates all 10 required files before extracting any
- [ ] Prints ✓ line for each file placed
- [ ] --force flag implemented (prevents silent overwrite without it)
- [ ] --dry-run flag implemented (validates + prints, no writes)
- [ ] Dry-run test passed with fixture zip in .test_folder/
- [ ] .test_folder/ empty after test

## Step 5: drop_zone and README
- [ ] tools/project_genesis/drop_zone/.gitkeep exists and is empty
- [ ] tools/project_genesis/README.md exists
- [ ] README has: What is Genesis, How to use it, What gets generated, Troubleshooting
- [ ] Troubleshooting section covers at least 3 deploy.py error scenarios
