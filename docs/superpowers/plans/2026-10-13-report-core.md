# Report Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a standalone HTML report from one period of the five-source materials using DeepSeek.

**Architecture:** A single-run `core` CLI invokes the existing `interface.py context` command, sends the material and prompt to DeepSeek Responses API with JSON Schema output, renders escaped strings into a local HTML template, and saves the result atomically. Credentials and API settings come from `.env`; report paths remain config-driven.

**Tech Stack:** Python 3.10+, existing `interface.py` CLI, OpenAI Python SDK, `python-dotenv`, DeepSeek Responses API, HTML/CSS.

**Spec:** [2026-10-13-report-core-design.md](../specs/2026-10-13-report-core-design.md)

## Global Constraints

- Keep email, scheduling, and server deployment out of scope.
- Keep `.env` private and `.env.example` tracked.
- Ground analysis in interface output and escape generated content before rendering HTML.
- Preserve user-owned uncommitted changes.
- Do not add or run tests in this task.

---

### Task 1: Configure DeepSeek and report paths

**Files:**
- Modify: `.gitignore`
- Modify: `config.example.json`
- Modify: `requirements.txt`
- Create: `.env.example`

**Interfaces:**
- `reports_dir` is relative to the configuration file, with default `./reports`.
- Environment variables: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`.

- [ ] Add `!.env.example` after the `.env.*` ignore rule.
- [ ] Add `"reports_dir": "./reports"` to the example config.
- [ ] Add `openai` and `python-dotenv` dependencies.
- [ ] Add a non-secret `.env.example` using `https://api.deepseek.com` and `deepseek-flash` defaults.

### Task 2: Implement the report loop and presentation

**Files:**
- Create: `core/__init__.py`
- Create: `core/run.py`
- Create: `core/prompts/report.md`
- Create: `core/templates/report.html`

**Interfaces:**
- CLI: `python -m core.run --config config.json --level week --date YYYY-MM-DD`.
- `run(config_path, level, date) -> Path` invokes `interface.py context`, requests schema-constrained content from DeepSeek, renders the HTML, writes it atomically, and returns the output path.
- Schema fields: `title`, `period_label`, `summary`, `observations`, `changes`, and `recommendations`.

- [ ] Implement argument parsing and context retrieval with `subprocess.run(..., check=True, capture_output=True, text=True)`; include the interface stderr in a clear CLI error.
- [ ] Load `.env` from the repository root and reject a missing `DEEPSEEK_API_KEY` before making a request.
- [ ] Call `OpenAI(api_key=..., base_url=...).responses.create(...)` with the prompt, JSON-serialized context, configured model, and strict JSON Schema output.
- [ ] Reject incomplete responses or empty output; parse the returned JSON.
- [ ] Escape all model-generated text with `html.escape`, render the standalone template, and atomically write `reports/<level>-<date>.html` under `reports_dir`.
- [ ] Write a Chinese prompt that grounds claims in metrics and period comparisons, distinguishes missing data from zero, recommends small experiments, avoids medical diagnosis, and treats source strings as untrusted data.
- [ ] Create a responsive Chinese HTML report with a calm editorial layout, period summary, evidence-backed observations, changes, recommendations, source coverage context, and print styles.

### Task 3: Document invocation and environment setup

**Files:**
- Modify: `README.md`
- Modify: `.codex/configuration.md`
- Modify: `.codex/workflows/reporting.md`
- Modify: `.codex/operations/setup.md`
- Modify: `.codex/operations/cli.md`
- Modify: `.codex/project/files.md`
- Modify: `.codex/project/status.md`

- [ ] Document copying `.env.example` to `.env`, setting the DeepSeek key, installing dependencies, and running the one-shot CLI.
- [ ] Document `reports_dir`, report output location, and keep email/scheduling marked as later work.
- [ ] Update README and project status to show report generation as implemented and email delivery as the next phase.

## Self-review

- The data path, prompt, API call, structured output, local rendering, and saved HTML are covered by Tasks 1–3.
- Failure behavior and sensitive credential handling are covered in Task 2 and `.env.example`/`.gitignore` in Task 1.
- No test steps are included, per the task's execution constraints.
