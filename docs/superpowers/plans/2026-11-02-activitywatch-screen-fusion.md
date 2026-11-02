# ActivityWatch + Screenshot Fusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use ActivityWatch AFK-aware intervals as the only PC time authority while retaining screenshot JSON as the semantic timeline and classification layer.

**Architecture:** Add one reusable ActivityWatch interval function in `interfaces/operator.py`. When `pc_screen_activity` is summarized, load ActivityWatch rows for the same period, intersect every screenshot sample with confirmed active intervals, and expose ActivityWatch total/coverage plus classified and unclassified semantic minutes. Keep the existing source-selection boundary so the report model receives one fused PC source rather than two conflicting totals.

**Tech Stack:** Python standard library, SQLite-backed existing operators, assert-based offline checks, static HTML.

**Spec:** `.codex/sources/pc-screen-activity.md`

## Global Constraints

- Do not add dependencies, a second model call, a new database, or a Windows collector.
- Screenshot samples never create PC minutes without ActivityWatch coverage.
- ActivityWatch `not-afk ∩ currentwindow` determines active time.
- Missing ActivityWatch coverage yields unavailable duration, not screenshot-estimated duration.
- Sensitive screenshot redaction and ActivityWatch fallback behavior remain intact.

---

### Task 1: AFK-aware semantic aggregation

**Files:**
- Modify: `interfaces/operator.py`
- Modify: `interfaces/summary.py`
- Modify: `interfaces/report.py`
- Test: `checks/screen.py`

**Interfaces:**
- Produces: `operator.pc_active_intervals(config, start, end, rows=None) -> list[tuple[datetime, datetime]]`.
- Extends: `summary.screen_activity(..., active_intervals=None)`; a provided list clips every screenshot sample to ActivityWatch-active seconds.
- Produces in fused summary: `activity_time_source`, `activity_time_available`, `activitywatch_coverage_minutes`, `classified_minutes`, and `unclassified_minutes`.

- [x] **Step 1: Write failing overlap and integration checks**

Create three five-minute screenshot samples and an ActivityWatch fixture active only from 10:02–10:07. Assert that the screenshot helper labels exactly 5 minutes, excludes the third screenshot, and truncates the timeline to 10:02–10:07. Through `summarize(pc_screen_activity)`, assert total time is 5 minutes rather than 15. Add a no-coverage range asserting duration is unavailable.

- [x] **Step 2: Run the check and verify RED**

Run: `/mnt/c/Users/33301/Documents/codefield/assets/self-harness/.venv/bin/python checks/screen.py`

Expected: failure because `screen_activity` does not accept `active_intervals` and screenshot reports still use sample duration.

- [x] **Step 3: Implement active interval extraction and clipping**

Extract the already-used `not-afk ∩ currentwindow` intersection into `pc_active_intervals`. In `screen_activity`, replace each nominal sample span with its intersections against the supplied intervals; use intersection endpoints for timeline boundaries and skip zero-overlap samples.

- [x] **Step 4: Fuse ActivityWatch into screenshot reports**

Load `pc_screen_time` rows once for the current/prior/trend window. For each screenshot calculation, compute ActivityWatch coverage and active intervals, set total minutes from the union of active intervals, retain classified semantic minutes from clipped screenshots, and report the remainder as unclassified. If coverage is absent, set total and daily average to `None` and emit an empty semantic timeline.

- [x] **Step 5: Run the check and verify GREEN**

Run: `/mnt/c/Users/33301/Documents/codefield/assets/self-harness/.venv/bin/python checks/screen.py`

Expected: the screenshot check reports ActivityWatch fusion and boundary coverage as passing.

### Task 2: Report contract, copy, and regression verification

**Files:**
- Modify: `core/run.py`
- Modify: `core/prompts/day.md`
- Modify: `checks/reporting.py`
- Modify: `.codex/sources/pc-screen-activity.md`
- Modify: `.codex/implementation/activities.md`
- Modify: `.codex/implementation/effective-data.md`
- Modify: `.codex/operations/verification.md`

**Interfaces:**
- Consumes: fused screenshot summary from Task 1.
- Produces: report copy that names ActivityWatch as time authority and screenshots as semantic samples.

- [x] **Step 1: Write the failing renderer check**

Provide a fused screenshot context with 295 active minutes, 210 classified minutes, and 85 unclassified minutes. Assert the report displays the ActivityWatch timing note and does not display the old “每张截图折算时间” wording.

- [x] **Step 2: Run the check and verify RED**

Run: `/mnt/c/Users/33301/Documents/codefield/assets/self-harness/.venv/bin/python checks/reporting.py`

Expected: failure on the new timing-authority copy.

- [x] **Step 3: Update renderer, prompt, and docs**

State that PC duration comes from ActivityWatch AFK/window intersections, screenshot JSON supplies semantics, and uncovered active minutes are unclassified. Tell the daily report model not to interpret screenshot sample count as time or visual focus as cognitive focus.

- [x] **Step 4: Run all offline verification**

Run every script under `checks/`, compile `interfaces` and `core`, and run `git diff --check`.

Expected: all commands exit 0 with no whitespace errors.
