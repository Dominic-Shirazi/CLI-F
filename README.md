# EndToEndDev 2.0 Autonomous Loop

This system runs a completely autonomous coding loop governed by LangGraph. It reads a master plan, uses Gemini to build code, employs a local LLM (GPT-OSS) to verify the code against success criteria, and utilizes Claude to audit the final changelog for critical scalability, logic, and security flaws. If Claude finds a critical issue, the loop will natively pause and alert you to intervene. Otherwise, the loop iterates through each step, dropping the fully verified code in the `/output` folder without human intervention.

## Installation Instructions

1. **Install Python Packages:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ollama Setup (for GPT-OSS):**
   Ensure you have [Ollama](https://ollama.com/) installed and running locally. Pull the `openhermes` model (or configure your preferred model in the code) used for the Inspector node:
   ```bash
   ollama pull openhermes
   ```

3. **Gemini CLI Setup:**
   Ensure you have a `gemini` executable CLI installed and available in your system path so the system can invoke Gemini for the Builder node.

4. **Claude Code CLI Setup:**
   Ensure you have the `claude` CLI installed and available in your system path so the system can invoke Claude for the Auditor node.

5. **API Keys:**
   Copy `.env.example` to `.env` and fill in your API keys (e.g., Anthropic, Gemini) required by the CLIs.
   ```bash
   cp .env.example .env
   ```

## Getting Started

To start a run from the beginning of `brain/MASTER_PLAN.md`:

```bash
python system/graph.py
```

## Crash Recovery

Because LangGraph uses a SQLite checkpointer (`system/checkpoints/langgraph_checkpoints.sqlite`), resuming after a crash or stoppage is fully supported. Just rerun the `graph.py` script with the same execution ID (if managed by a CLI wrapper) or the script will pick up where the DB left off.

## Responding to a CEO Interrupt

If the LangGraph loop pauses due to a **CRITICAL** severity audit finding from Claude, it will wait for your input. 

1. Review the generated `audit_trail/claude_audit_notes.md`.
2. Review the code diff in `workspace/diffs/latest_diff.patch`.
3. If necessary, manually tweak the code or leave a note.
4. Resume the graph execution through the LangGraph interface (or your runner script) providing any feedback. The loop will route back to Gemini to try again.
