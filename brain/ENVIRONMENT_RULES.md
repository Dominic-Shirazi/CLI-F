# Environment Rules — Fail the step if any are violated

1. All Python test commands must have used the activated venv (`venv/Scripts/activate`) or conda env
2. reasoning.md must exist, be non-empty, and must not have a To Do list that includes action items
   within the current step
3. `.test_folder/` must be empty or deleted — no leftover test artifacts (when returning from
   Claude's review with a 'PASS' verdict)
4. Flag RETURN if reasoning.md contains "I assumed", "I think", or any open TODO
5. Flag QUESTION if Gemini's reasoning indicates "PARTIAL" for a completion status
6. Flag NEEDS_REVIEW if Gemini's reasoning includes anything that indicates it "NEEDS_REVIEW"
7. Flag RETURN any step where git diff includes changes to: reasoning.md, current_task.md,
   audit_trail/, status/
