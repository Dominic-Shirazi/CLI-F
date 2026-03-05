Gemini was told to: {current_task}
Gemini says it did: {reasoning_summary}
Files changed: {diff_stat}

Verdict — output ONLY one line:
PASS                          → work complete, send to reviewer
INCOMPLETE: <one sentence>    → partial, send back to Gemini
FAIL: <one sentence>          → wrong direction, send back to Gemini
QUESTION: <one sentence>      → Gemini has a blocker, ping CEO
