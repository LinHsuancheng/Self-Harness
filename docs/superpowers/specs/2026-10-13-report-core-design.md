# Report Core Design

## Goal

Generate a standalone HTML report for one requested period from the five-source material already produced by `interface.py`.

## Scope

The first version is a single-run CLI. It reads the report prompt and HTML template, invokes DeepSeek, renders the structured result locally, saves the HTML, and prints its path. Email and scheduling remain out of scope.

## Data flow

1. Invoke `interface.py context` with the selected period and configured data paths; parse its JSON output.
2. Read the analysis prompt and standalone HTML template from `core/`.
3. Send the prompt and period material to DeepSeek through the OpenAI Python SDK Responses API. Read API credentials and endpoint settings from an ignored `.env` file (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`).
4. Require a fixed JSON Schema result containing a title, summary, observations, changes, and recommendations. The prompt grounds claims in the supplied material, calls out missing data, avoids medical diagnosis, and treats source text as data rather than instructions.
5. Render report fields into escaped HTML, write atomically under the configured reports directory, and print the resulting path.

DeepSeek's documented base URL is `https://api.deepseek.com`; model and endpoint remain configurable. Use the Responses `text.format` JSON Schema mode supported by DeepSeek.

## Files

- `core/run.py`: CLI, interface subprocess, DeepSeek request, rendering, and atomic output.
- `core/prompts/report.md`: report analysis instructions and required content.
- `core/templates/report.html`: responsive standalone visual template.
- `.env.example`: variable names and non-secret defaults; `.env` remains ignored.
- `.gitignore`: keep `.env` and generated reports private while allowing `.env.example` to be tracked.
- `config.example.json`: reports output directory and existing interface data paths.
- `requirements.txt`: OpenAI SDK and `.env` loader dependencies.

## Failure behavior

Missing credentials, failed interface runs, API errors, incomplete responses, invalid structured output, and output errors terminate with a clear message. A failed run does not replace an existing report.

## Out of scope

Email delivery, recurring schedules, historical report context, report database, and deployment to the server.

The default generated report directory is Git-ignored because reports contain personal material. If `reports_dir` points inside the repository elsewhere, that path must be ignored separately.
