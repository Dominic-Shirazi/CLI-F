# Project Genesis Tool

## What is Genesis?
Project Genesis is a standalone bootstrapping tool for EndToEndDev that uses a conversational AI interview to generate your project's configuration. It eliminates the cold-start problem by providing a perfectly formatted "brain" for your autonomous agents.

## How to use it
1.  **Start the Interview:** Open your preferred web AI (Gemini, ChatGPT, or Claude) and paste the entire content of `tools/project_genesis/GENESIS_PROMPT.md`.
2.  **Answer Questions:** The "Project Architect" AI will interview you about your project's vision, tech stack, and goals.
3.  **Generate:** Once the interview is complete, tell the AI to "**GENERATE**". It will provide a download link for `genesis_output.zip`.
4.  **Drop the Zip:** Place the downloaded `genesis_output.zip` into the `tools/project_genesis/drop_zone/` directory.
5.  **Deploy:** From the project root, run: `python tools/project_genesis/deploy.py`.
6.  **Finalize:** Open the newly created `.env` file, add your API keys, and start your project with `python main.py`.

## What gets generated
| File | Destination in project |
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

## Troubleshooting
- **No .zip files found:** Ensure the AI-generated zip is named correctly and placed exactly in `tools/project_genesis/drop_zone/`.
- **Multiple .zip files found:** The deploy script only handles one zip at a time. Delete old zips from the drop zone before deploying a new one.
- **Required files missing:** If the AI failed to include all 10 files, go back to the chat and ask it to "Regenerate the zip with all required files: [list the missing ones]".
