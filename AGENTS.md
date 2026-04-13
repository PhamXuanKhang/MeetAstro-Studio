# Agent Guidelines

## Mandatory Rules When Using AI Coding Agents

### 1. AI Prompt Logging (Automatic)

Prompts are **automatically logged** via hooks when you use any supported AI tool.
You do **not** need to manually update `PROMPT_LOG.md`.

Supported tools and their hook configs:
| Tool | Config file |
|---|---|
| Claude Code | `.claude/settings.json` |
| Cursor | `.cursor/hooks.json` |
| OpenAI Codex | `.codex/hooks.json` |
| Gemini CLI | `.gemini/settings.json` |
| GitHub Copilot | `.github/hooks/hooks.json` |

Logs are saved to `.ai-log/session.jsonl` and submitted automatically on `git push`.

### 2. Setup (One-time)

```bash
# Install git pre-push hook
bash scripts/setup_hooks.sh
```

`AI_LOG_SERVER` and `AI_LOG_API_KEY` are already set in `.env.example`.

### 3. Pull Request Requirements

- **Title**: Short description of the change
- **Description**: Must include:
  - Summary of changes
  - List of changed files

PR description format:

```
## Summary
<description of changes>

## Changes
- <list of changed files>
```

### 4. Rules for AI Agents

If you are an AI coding agent (Claude Code, Cursor, Copilot, Codex, Gemini, etc.):

- **MUST NOT** create a PR without first ensuring `bash scripts/setup_hooks.sh` has been run
- **MUST** include a clear PR description with summary and changed files
- **DO NOT** commit `.ai-log/*.jsonl` files (they are gitignored)
- Logging happens automatically — do not ask users to log prompts manually

### 5. Project-specific rules

- Extend this file with team conventions when you add workflows, tools, or policies that agents should follow.

### 6. Secrets and credentials

- **DO NOT** commit API keys, passwords, or other secrets. Use `.env` locally (gitignored) and document required variables in `.env.example` only.

### 7. Scope of work

- Keep changes limited to what the user asked for. Avoid unrelated refactors, drive-by cleanups, or extra files unless they are required to deliver the request.

### 8. Shared hook logger

- `scripts/log_hook.py` is used by every tool listed in section 1. When reading hook JSON from stdin, decode with `utf-8-sig` so a UTF-8 BOM (e.g. from Cursor on Windows) does not break `json.loads`.
- Pass the tool name as the first CLI argument (e.g. `python scripts/log_hook.py cursor`). The `AI_TOOL_NAME=value` prefix is Unix-only and fails on Windows CMD/PowerShell; the script still accepts `AI_TOOL_NAME` as a fallback for older configs.

### 9. Keeping hook configs in sync

- If you add a tool, change hook commands, or change how `log_hook.py` is invoked, update the table in section 1 and every matching config under `.claude/`, `.cursor/`, `.codex/`, `.gemini/`, and `.github/hooks/` so all environments behave the same.
