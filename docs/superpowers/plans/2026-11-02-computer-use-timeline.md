# Computer-use Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn daily screenshot-analysis JSON records into a readable computer-use timeline in the Self Harness morning report.

**Architecture:** Extend the existing deterministic screenshot aggregation with daily-only timeline sessions. Consecutive samples merge when their semantic category and activity match; idle samples, semantic changes, and gaps longer than one sample split sessions. Render the resulting sessions directly in the static HTML report without another model call or dependency.

**Tech Stack:** Python standard library, existing assert-based checks, static HTML/CSS.

**Spec:** `.codex/sources/pc-screen-activity.md`

## Global Constraints

- Do not read `raw/`, `database/`, `reports/`, or credential values.
- Do not add dependencies or another model call.
- Emit timeline only for day reports; longer periods retain compact distributions.
- Sensitive samples must never expose app, title, URL, topics, or summary.
- ActivityWatch remains the fallback when screenshot coverage is below `report_min_samples`.

---

### Task 1: Deterministic screenshot sessions

**Files:**
- Modify: `interfaces/summary.py:155-235`
- Modify: `interfaces/report.py:143-225`
- Test: `checks/screen.py`

**Interfaces:**
- Consumes: ordered `pc_screen_activity` materials already passed to `screen_activity(...)`.
- Produces: `screen_activity(..., include_timeline=True)` with `timeline: list[dict]`; each session contains `start`, `end`, `minutes`, `category`, `activity`, `focus`, `apps`, `topics`, `summary`, `sample_count`, and `average_confidence`.

- [x] **Step 1: Write the failing aggregation check**

Add synthetic samples showing that two consecutive coding samples merge, a semantic change splits, idle stays visible, a gap splits, and sensitive content remains redacted. Assert exact session boundaries and fields.

- [x] **Step 2: Run the check and verify RED**

Run: `/mnt/c/Users/33301/Documents/codefield/assets/self-harness/.venv/bin/python checks/screen.py`

Expected: failure because `screen_activity()` does not accept `include_timeline` or return `timeline`.

- [x] **Step 3: Implement the minimum sessionizer**

Reuse the existing duration calculation. Merge adjacent samples when the gap is no greater than `sample_minutes` and their session keys match: all idle samples share one key, all sensitive samples share one key, and active samples use `category` plus `activity`. Deduplicate apps/topics in encounter order, use the latest non-empty summary, compute dominant focus, and round duration/confidence at finalization. Sensitive sessions remain fully sanitized.

- [x] **Step 4: Expose timeline only for day reports**

Call `screen_activity(..., include_timeline=level == 'day')`; remove `timeline` alongside other daily detail for longer periods.

- [x] **Step 5: Run the check and verify GREEN**

Run: `/mnt/c/Users/33301/Documents/codefield/assets/self-harness/.venv/bin/python checks/screen.py`

Expected: `PASS: screenshot identity, duplicate capture, sensitive redaction, aggregation, timeline and boundary cap`.

### Task 2: Static daily timeline rendering

**Files:**
- Modify: `core/run.py:120-370`
- Modify: `core/templates/report.html`
- Modify: `core/prompts/day.md`
- Test: `checks/reporting.py`

**Interfaces:**
- Consumes: `context['pc_screen_activity']['summary']['timeline']`.
- Produces: escaped `PC_TIMELINE` HTML, or an empty-state message for ActivityWatch/fallback reports.

- [x] **Step 1: Write the failing renderer check**

Extend the synthetic screenshot context with coding, idle, and sensitive sessions. Assert that local time, activity summary, app/topic labels, idle copy, and sanitized sensitive copy appear, and raw unsafe markup is escaped.

- [x] **Step 2: Run the check and verify RED**

Run: `/mnt/c/Users/33301/Documents/codefield/assets/self-harness/.venv/bin/python checks/reporting.py`

Expected: failure because the template has no timeline block.

- [x] **Step 3: Implement the renderer and styles**

Add one small `_timeline(...)` helper in `core/run.py`, populate `PC_TIMELINE`, and add a `Computer-use Timeline` section inside the existing PC card. Use semantic HTML and the existing color tokens; do not add JavaScript.

- [x] **Step 4: Run the check and verify GREEN**

Run: `/mnt/c/Users/33301/Documents/codefield/assets/self-harness/.venv/bin/python checks/reporting.py`

Expected: `PASS: current schema, escaped content, static report, explicit period metadata, screenshot PC timeline and old-source fallback`.

### Task 3: Contract documentation and regression verification

**Files:**
- Modify: `.codex/sources/pc-screen-activity.md`
- Modify: `.codex/implementation/activities.md`
- Modify: `.codex/operations/verification.md`

**Interfaces:**
- Consumes: the shipped timeline contract and rendering behavior.
- Produces: current documentation describing daily session boundaries, privacy behavior, and verification coverage.

- [x] **Step 1: Document the daily timeline contract**

State the exact merge/split rules, fields, daily-only scope, and that no second model call occurs.

- [x] **Step 2: Run all offline checks**

Run all six files listed by `rg --files checks` with the repository virtualenv Python.

Expected: every check exits 0.

- [x] **Step 3: Review the final diff**

Run: `git diff --check && git status --short && git diff --stat`

Expected: no whitespace errors; only the planned source, check, template, documentation, and plan files changed.
