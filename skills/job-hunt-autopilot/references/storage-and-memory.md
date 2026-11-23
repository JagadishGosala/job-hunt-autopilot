# Storage and memory

## The store

Every file lives under the prefix `job-hunt/`:

| File | What it holds | Written by |
|---|---|---|
| `settings.json` | Preferences, portals, limits, consents, search queries | setup |
| `master-resume.json` | The truth: every fact the candidate can claim | setup (the candidate approves changes) |
| `spec-master.json` | Untailored resume layout | setup |
| `answer-bank.json` | The candidate's own answers to application questions, plus notes on their writing voice | answer mode, Applier |
| `jobs.json` | `{"jobs": {job_id: {...}}}`: every job and its stage | all roles |
| `shortlist.json` | The last numbered shortlist shown, `{"presented_at", "items": [{"n", "job_id"}]}` | discover |
| `questions.json` | `{"questions": {id: {...}}}`: open application questions | Applier |
| `scout-actors.json` | Which job-board scrapers work, per portal (starts from the template) | Scout |
| `companies/<slug>.md` | Company dossiers (reused for 30 days) | Ranker |
| `tailored/<job_id>.json` | Final tailored resume specs | Tailor |
| `run-logs/Run log - <YYYY-MM-DD> <Day> - <mode>.md` | One per run | orchestrator |
| `history.csv` | One row per job reaching applied / drafted / blocked / skipped | Applier |

Schemas are in `schemas.md`.

### Backends

- **Project docs:** `project_read` / `project_write` with the path, for example `job-hunt/jobs.json`. There's no partial update: read, change, and write the whole file. Write `jobs.json` after each stage change in a batch, not after every field.
- **Local folder:** `device_stage_files` → edit the staged copy → copy it to `/mnt/user-data/outputs/<name>` → `device_commit_files` with `expectedMtimeMs`. If the commit is rejected because the file changed, re-stage and redo the edit.
- **Session only:** plain files in `/home/claude/job-hunt/store/`.

**Concurrency:** only one run at a time. At the start of discover and apply, write `run_lock: {mode, started_at}` into `jobs.json`. If another lock is under 3 hours old, say a run is already in progress and stop. Clear the lock at the end.

**Local output folder** (`settings.output_folder`; required for tailored uploads): save each tailored resume PDF there before uploading it, because Chrome can only upload files that are on the candidate's computer. Name it `Resume for <Company> - <Title> (<Portal>) - <YYYY-MM-DD>.pdf`. Also save a copy of each run log there. Always deliver files through `device_commit_files`.

## Memory

Claude's memory makes the candidate's answers available in any chat, even outside this skill. The store is still the **source of truth**:

- Memory files are size-limited.
- Some facts (pay, for example) may be refused by memory's privacy settings.
- Scheduled runs might not see memory.

Use memory only if the candidate said yes at setup (`settings.memory.enabled`).

**Where:** one file, `/areas/job-hunt.md`. When the session is bound to a claude.ai Project, memory writes must go under that Project's memory folder (`/projects/<project-id>/areas/job-hunt.md`); the memory tool's instructions name that folder. Read before writing, and pass `if_version`.

**Format:**

```markdown
---
name: job-hunt
description: Job search set up with job-hunt-autopilot: store location, targets, standing application answers
sources: [chat]
aliases: [job search, job hunt, applications]
---
- [stated] store: project docs job-hunt/   (or: folder E:\Jobs\job-hunt\ on <device>)
- [stated] targets backend / full-stack roles; Hyderabad, remote or hybrid; 6 years experience
- [stated] notice: 30 days; earliest joining 2026-12-15
- [stated] excluded employers: <current employer>
## Application answers
- [stated] Q "Why are you looking for a change?" → "<their exact words>"
- [stated] Q "Willing to relocate?" → Yes
```

**Rules:**

- Only the candidate's own words go in, tagged `[stated]`. Never save composed or adapted answers, scores, or anything you inferred.
- Write pay figures in their **own** memory write, after the other writes. If memory refuses it, tell the candidate in one line and carry on: the store has it.
- **Never** save passwords, OTPs, ID or account numbers, or protected personal attributes asked on demographic forms.
- **Keep it short.** One line per answer, newest first. Over roughly 40 answers, keep only reusable non-company-specific ones and point to the store for the rest.
- When an answer changes (for example a new joining date), replace the line; don't append.

**On a run without a store:** if memory has the `store:` line, use it to find the store. If memory has answers but the store has none (for example after the candidate deleted the project), offer to rebuild `answer-bank.json` from memory.
